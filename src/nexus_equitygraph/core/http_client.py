"""HTTP Client module with retry logic and centralized configuration."""

from functools import lru_cache
from typing import Any, Dict, Optional

import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    """Wrapper around requests.Session with retry logic and default headers."""

    # Default headers used for all requests to avoid being blocked by servers.
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        base_url: str = "",
        *,
        headers: Optional[Dict[str, str]] = None,
        retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: int = 30,
    ) -> None:
        """Initializes the HttpClient with retry strategy and default headers.

        Args:
            base_url (str, optional): Base URL for the API. Defaults to "".
            headers (Optional[Dict[str, str]], optional): Additional headers to include. Defaults to None.
            retries (int, optional): Number of retry attempts for failed requests. Defaults to 3.
            backoff_factor (float, optional): Backoff factor for retries. Defaults to 0.5.
            timeout (int, optional): Timeout for requests in seconds. Defaults to 30.
        """

        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

        # Initialize session headers with defaults, allowing overrides from the 'headers' argument.
        self.session.headers.update(self.DEFAULT_HEADERS | (headers or {}))

        # Configure the retry strategy and mount adapters.
        self._setup_retry_strategy(retries, backoff_factor)

    def __enter__(self) -> "HttpClient":
        """Enter the context manager."""

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager and close the session."""

        self.close()

    def close(self):
        """Close the session."""

        if self.session:
            self.session.close()

    def _setup_retry_strategy(self, retries: int, backoff_factor: float) -> None:
        """Configures the retry strategy and mounts it to the session.

        Args:
            retries (int): Number of retry attempts.
            backoff_factor (float): Backoff factor for retries.
        """

        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Perform a GET request with automatic error handling.

        Args:
            endpoint (str): The API endpoint to request.
            **kwargs: Additional arguments to pass to requests.get().

        Returns:
            requests.Response: The response object.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
            requests.exceptions.HTTPError: For HTTP error responses.
        """

        url = f"{self.base_url}{endpoint}" if self.base_url else endpoint

        # Set default timeout if not provided
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as http_error:
            # Re-raise HTTP errors after logging for visibility.
            logger.error(f"HTTP error occurred: {url} - {http_error}")
            raise http_error
        except requests.exceptions.RequestException as request_exception:
            logger.error(f"Request failed: {url} - {request_exception}")
            raise request_exception


@lru_cache(maxsize=1)
def get_http_client() -> HttpClient:
    """Factory to get the HTTP client instance (Singleton).

    Returns a cached singleton instance of HttpClient for connection reuse.
    The session maintains a connection pool per domain, improving performance
    when making multiple requests to the same hosts.

    Returns:
        HttpClient: The configured HTTP client instance.
    """

    return HttpClient()
