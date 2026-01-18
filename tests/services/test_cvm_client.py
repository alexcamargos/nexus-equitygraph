"""Tests for CVMClient service."""

import pytest
import requests
import pandas as pd
from nexus_equitygraph.services.cvm_client import CVMClient


@pytest.fixture
def mock_http(mocker):
    """Fixture for mocking HTTP client."""

    return mocker.Mock()


@pytest.fixture
def mock_caches(mocker):
    """Fixture for mocking file and pickle caches."""

    return {"file": mocker.Mock(), "pickle": mocker.Mock()}


class TestCVMClient:
    """Tests for the CVMClient service."""

    @pytest.fixture
    def cvm_client(self, mock_http, mock_caches):
        """Fixture for a pre-configured CVMClient."""

        return CVMClient(
            http_client=mock_http,
            file_cache=mock_caches["file"],
            pickle_cache=mock_caches["pickle"],
        )

    def test_cvm_client_initialization(self, cvm_client, mock_http, mock_caches):
        """Tests CVMClient initialization with dependencies."""

        # Assert: Verify that the client is initialized with the provided dependencies.
        assert cvm_client.http_client == mock_http
        assert cvm_client.file_cache == mock_caches["file"]
        assert cvm_client.pickle_cache == mock_caches["pickle"]

    def test_cvm_client_context_manager(self, mock_http):
        """Tests if context manager closes the http client."""

        # Action: Use the client as a context manager.
        with CVMClient(http_client=mock_http) as client:
            assert client.http_client == mock_http
        # Assert: Verify that the HTTP client is closed upon exit.
        mock_http.close.assert_called_once()

    def test_get_cadastral_info_cache_hit(self, cvm_client, mocker, mock_http, mock_caches):
        """Tests cadastral info retrieval with cache hit."""

        # Setup: Mock the CSV parser and simulate a file cache hit.
        mock_parse = mocker.patch("nexus_equitygraph.services.cvm_parser.parse_cadastral_csv")
        mock_caches["file"].load_cache.return_value = b"csv_content"
        mock_parse.return_value = pd.DataFrame({"CD_CVM": ["123"]})

        # Action: Retrieve cadastral info.
        df = cvm_client.get_cadastral_info()

        # Assert: Verify that data is returned from cache without HTTP calls.
        assert not df.empty
        mock_http.get.assert_not_called()
        mock_caches["file"].load_cache.assert_called_once()

    def test_get_cadastral_info_cache_miss(self, cvm_client, mocker, mock_http, mock_caches):
        """Tests cadastral info retrieval with cache miss."""

        # Setup: Mock the CSV parser and simulate a file cache miss.
        mock_parse = mocker.patch("nexus_equitygraph.services.cvm_parser.parse_cadastral_csv")
        mock_caches["file"].load_cache.return_value = None
        mock_http.get.return_value.content = b"downloaded_content"
        mock_parse.return_value = pd.DataFrame({"CD_CVM": ["456"]})

        # Action: Retrieve cadastral info.
        df = cvm_client.get_cadastral_info()

        # Assert: Verify that data is downloaded and saved to cache.
        assert not df.empty
        mock_http.get.assert_called_once()
        mock_caches["file"].save_cache.assert_called_once()

    def test_get_consolidated_company_data_flow(self, cvm_client, mocker, mock_caches):
        """Tests the full flow of consolidated company data retrieval."""

        # Setup: Mock company resolution and financial data fetching.
        mock_resolve = mocker.patch("nexus_equitygraph.services.cvm_client.CVMClient.get_cvm_code_by_name")
        mock_fetch = mocker.patch("nexus_equitygraph.services.cvm_client.CVMClient._fetch_historical_financials")
        mock_resolve.return_value = "1234"
        mock_caches["pickle"].load_cache.return_value = None
        mock_fetch.return_value = {"BPA": pd.DataFrame()}

        # Action: Retrieve consolidated data for a company.
        data = cvm_client.get_consolidated_company_data("WEGE3", years_back=1)

        # Assert: Verify that the data is fetched and saved to the pickle cache.
        assert "BPA" in data
        mock_fetch.assert_called_once_with("1234", years_back=1)
        mock_caches["pickle"].save_cache.assert_called_once()

    def test_get_consolidated_company_data_not_found(self, cvm_client, mocker):
        """Tests error handling when company is not found in CVM."""

        # Setup: Mock the company resolution to return None.
        mocker.patch.object(CVMClient, "get_cvm_code_by_name", return_value=None)

        # Action & Assert: Verify that a ValueError is raised when the company is not found.
        with pytest.raises(ValueError, match="não encontrada na CVM"):
            cvm_client.get_consolidated_company_data("UNKNOWN")

    def test_list_available_itr_years_success(self, cvm_client, mocker, mock_http):
        """Tests successful retrieval of available years from CVM."""

        # Setup: Mock the HTML year extractor and the HTTP response.
        mock_extract = mocker.patch(
            "nexus_equitygraph.services.cvm_parser.extract_years_from_html", return_value=[2023, 2022]
        )
        mock_http.get.return_value.content = b"html_content"

        # Action: List available ITR years.
        years = cvm_client.list_available_itr_years()

        # Assert: Verify that the years are correctly extracted from the HTML.
        assert years == [2023, 2022]
        mock_extract.assert_called_once()

    def test_list_available_itr_years_fallback(self, cvm_client, mocker, mock_http):
        """Tests fallback mechanism when CVM portal is down."""

        # Setup: Simulate a network error and mock the fallback year generator.
        mock_http.get.side_effect = Exception("Connection Error")
        mock_fallback = mocker.patch(
            "nexus_equitygraph.services.cvm_registry.get_fallback_years", return_value=[2024, 2023]
        )

        # Action: List available ITR years with fallback enabled.
        years = cvm_client.list_available_itr_years(fallback_years=2)

        # Assert: Verify that fallback years are returned.
        assert years == [2024, 2023]
        mock_fallback.assert_called_once_with(2)

    def test_get_itr_data_not_found(self, cvm_client, mocker, mock_http):
        """Tests that ITR missing data raises FileNotFoundError."""

        # Setup: Mock a 404 error during file download.
        response = requests.Response()
        response.status_code = 404
        error = requests.exceptions.HTTPError(response=response)
        mocker.patch.object(cvm_client, "_download_file", side_effect=error)

        # Action & Assert: Verify that FileNotFoundError is raised for missing ITR data.
        with pytest.raises(FileNotFoundError, match="ITR data for year 2023 not found"):
            cvm_client.get_itr_data("1234", 2023)

    def test_get_dfp_data_not_found(self, cvm_client, mocker):
        """Tests that DFP missing data returns empty dict gracefully."""

        # Setup: Mock a 404 error during file download.
        response = requests.Response()
        response.status_code = 404
        mocker.patch.object(cvm_client, "_download_file", side_effect=requests.exceptions.HTTPError(response=response))

        # Action & Assert: Verify that an empty dictionary is returned gracefully.
        assert cvm_client.get_dfp_data("1234", 2023) == {}
