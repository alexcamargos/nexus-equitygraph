"""Test for the Market Resolver service."""

import pytest
import requests

from nexus_equitygraph.services.market_resolver import resolve_name_from_ticker


class TestMarketResolver:
    """Tests for the Market Resolver service."""

    @pytest.fixture
    def mock_yf_ticker(self, mocker):
        """Fixture for mocking yfinance.Ticker."""

        return mocker.patch("yfinance.Ticker")

    @pytest.fixture
    def mock_instance(self, mocker):
        """Fixture for the mocked instance of Ticker."""

        return mocker.Mock()

    def test_resolve_name_from_ticker_success(self, mock_yf_ticker, mock_instance):
        """Tests if ticker resolution works correctly."""

        # Setup: Mock the YFinance Ticker instance with company names.
        mock_instance.info = {"longName": "WEG S.A.", "shortName": "WEG"}
        mock_yf_ticker.return_value = mock_instance

        # Action: Resolve names for various ticker formats.
        result = resolve_name_from_ticker("WEGE3")

        # Assert: Verify that the correct short names are returned.
        assert result == "WEG"

        result = resolve_name_from_ticker("WEGE3.SA")
        assert result == "WEG"

        mock_instance.info = {"shortName": "BANCO SANTANDER BRASIL"}
        mock_yf_ticker.return_value = mock_instance
        assert resolve_name_from_ticker("SANB11.SA") == "BANCO SANTANDER BRASIL"
        assert resolve_name_from_ticker("SANB11") == "BANCO SANTANDER BRASIL"

    def test_resolve_name_from_ticker_lowercase(self, mock_yf_ticker, mock_instance):
        """Tests if ticker resolution is case insensitive."""

        # Setup: Mock the YFinance Ticker instance.
        mock_instance.info = {"shortName": "VALE"}
        mock_yf_ticker.return_value = mock_instance

        # Action & Assert: Verify that the correct name is returned with lowercase ticker.
        assert resolve_name_from_ticker("vale3") == "VALE"

    def test_resolve_name_from_ticker_name_priority(self, mock_yf_ticker, mock_instance):
        """Tests if shortName is prioritized over longName."""

        # Setup: Mock the YFinance Ticker instance with only a long name.
        mock_instance.info = {"longName": "PETROLEO BRASILEIRO S.A."}
        mock_yf_ticker.return_value = mock_instance

        # Action & Assert: Verify that the long name is processed and returned when short name is missing.
        assert resolve_name_from_ticker("PETR4") == "PETROLEO BRASILEIRO"

    def test_resolve_name_from_ticker_empty_input(self):
        """Tests if empty input returns None."""

        # Action & Assert: Verify that empty or null inputs return None.
        assert resolve_name_from_ticker("") is None
        assert resolve_name_from_ticker(None) is None

    def test_resolve_name_from_ticker_invalid_format(self):
        """Tests if invalid ticker formats return None."""

        # Action & Assert: Verify that invalid ticker formats return None without calling YFinance.
        assert resolve_name_from_ticker("INVALID_TICKER") is None
        assert resolve_name_from_ticker("12345") is None

    def test_resolve_name_from_ticker_network_error(self, mock_yf_ticker):
        """Tests if network errors are handled gracefully."""

        # Setup: Simulate a connection error in the YFinance client.
        mock_yf_ticker.side_effect = requests.exceptions.ConnectionError("Timeout")

        # Action & Assert: Verify that network errors are handled and return None.
        assert resolve_name_from_ticker("VALE3") is None

    def test_resolve_name_from_ticker_no_info(self, mock_yf_ticker):
        """Tests if no company name found returns None."""

        # Setup: Mock a Ticker instance with empty info.
        mock_yf_ticker.return_value.info = {}

        # Action & Assert: Verify that None is returned when no company info is found.
        assert resolve_name_from_ticker("MGLU3") is None
