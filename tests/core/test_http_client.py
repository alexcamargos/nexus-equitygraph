"""Tests for the HttpClient in nexus_equitygraph.core.http_client."""

import pytest
from requests.exceptions import HTTPError, RequestException

from nexus_equitygraph.core.http_client import HttpClient


class TestHttpClient:
    """Test suite for HttpClient."""

    @pytest.fixture
    def client(self):
        """Fixture providing a default HttpClient instance."""

        return HttpClient()

    @pytest.fixture
    def mock_response(self, mocker):
        """Fixture providing a mock response object."""

        return mocker.Mock()

    def test_initialization_defaults(self, client):
        """Test default initialization values."""

        # Assert: Verify if default values are correct.
        assert client.base_url == ""
        assert client.timeout == 30
        assert "User-Agent" in client.session.headers
        assert client.session.headers["User-Agent"] == HttpClient.DEFAULT_HEADERS["User-Agent"]

    def test_initialization_custom(self):
        """Test initialization with custom values."""

        # Arrange: Define custom headers.
        headers = {"Authorization": "Bearer token"}

        # Action: Instantiate the client with custom settings.
        client = HttpClient(base_url="https://api.test.com", headers=headers, timeout=60)

        # Assert: Verify if custom values were applied.
        assert client.base_url == "https://api.test.com"
        assert client.timeout == 60
        assert client.session.headers["Authorization"] == "Bearer token"

    def test_get_success(self, mocker, mock_response):
        """Test successful GET request."""

        # Arrange: Setup response mock and instantiate the client.
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}

        mock_get = mocker.patch("requests.Session.get", return_value=mock_response)

        client = HttpClient(base_url="https://api.test.com")

        # Action: Execute GET request.
        response = client.get("/endpoint")

        # Assert: Verify if the request was made correctly and the return is as expected.
        mock_get.assert_called_once_with("https://api.test.com/endpoint", timeout=30)
        assert response.status_code == 200
        assert response.json() == {"key": "value"}

    def test_get_http_error(self, client, mocker, mock_response):
        """Test GET request raising HTTPError."""

        # Arrange: Setup mock to simulate an HTTP 404 error.
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("Not Found")

        mocker.patch("requests.Session.get", return_value=mock_response)

        # Action & Assert: Attempt to execute the request and verify if HTTPError is raised.
        with pytest.raises(HTTPError):
            client.get("https://api.test.com/404")

    def test_get_request_exception(self, client, mocker):
        """Test GET request raising RequestException (network error)."""

        # Arrange: Setup mock to simulate a connection error.
        mocker.patch("requests.Session.get", side_effect=RequestException("Connection Error"))

        # Action & Assert: Attempt to execute the request and verify if RequestException is raised.
        with pytest.raises(RequestException):
            client.get("https://api.test.com/error")

    def test_close(self, client, mocker):
        """Test closing the session."""

        # Arrange: Mock the internal session close method.
        mock_close = mocker.patch.object(client.session, "close")

        # Action: Call the client close method.
        client.close()

        # Assert: Verify if the session close method was called.
        mock_close.assert_called_once()

    def test_retry_strategy_configuration(self, client):
        """Test if the retry strategy is correctly configured on the session."""

        # Arrange: Client is already instantiated by fixture.

        # Action: (Inspection of state)

        # Assert: Verify adapters are mounted for http and https.
        assert "https://" in client.session.adapters
        assert "http://" in client.session.adapters

        # Assert: Verify retry configuration details.
        adapter = client.session.adapters["https://"]
        assert adapter.max_retries.total == 3
        assert adapter.max_retries.backoff_factor == 0.5

    def test_get_passes_kwargs(self, client, mocker, mock_response):
        """Test if additional arguments (like params) are passed to the request."""

        # Arrange: Setup mock.
        mock_response.status_code = 200
        mock_get = mocker.patch("requests.Session.get", return_value=mock_response)
        params = {"search": "term"}

        # Action: Call get with extra parameters.
        client.get("/endpoint", params=params)

        # Assert: Verify params were passed to the session.
        mock_get.assert_called_once_with("/endpoint", timeout=30, params=params)
