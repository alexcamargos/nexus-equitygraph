"""Client for interacting with the CVM Open Data Portal."""

import concurrent.futures
from datetime import timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from loguru import logger

from nexus_equitygraph.core.cache import get_file_cache_manager, get_pickle_cache_manager
from nexus_equitygraph.core.http_client import HttpClient
from nexus_equitygraph.core.settings import cvm_settings
from nexus_equitygraph.core.text_utils import format_cache_key
from nexus_equitygraph.services import cvm_parser, cvm_registry


class CVMClient:
    """Client for interacting with the CVM Open Data Portal.

    Focused on retrieving ITR (Quarterly Information) documents.
    """

    # Maximum number of concurrent threads for I/O operations.
    MAX_CONCURRENT_DOWNLOADS = 5

    # Static filename for the global cadastral registry.
    CVM_CADASTRAL_FILENAME = "cad_cia_aberta.csv"

    # Default durations and timeouts for caching and requests.
    CADASTRAL_CACHE_DURATION = timedelta(hours=24)
    FINANCIAL_CACHE_DURATION = timedelta(days=30)
    DEFAULT_TIMEOUT = 30
    REPORT_TIMEOUT = 60
    LIST_YEARS_TIMEOUT = 10

    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        *,
        file_cache: Optional[Any] = None,
        pickle_cache: Optional[Any] = None,
        timeout: int = 30,
    ) -> None:
        """Initialize the CVMClient.

        Args:
            http_client (Optional[HttpClient]): Custom HTTP client. If None, a default one is created.
            file_cache (Optional[Any]): Cache manager for raw files.
            pickle_cache (Optional[Any]): Cache manager for processed data.
            timeout (int): Timeout for HTTP requests in seconds. Default is 30.
        """

        # Use the injected http client or create a new one with a default timeout.
        self.http_client = http_client or HttpClient(timeout=timeout)
        # Use the injected cache managers or create new ones if factories are available.
        self.file_cache = file_cache or (
            get_file_cache_manager() if get_file_cache_manager else None
        )
        self.pickle_cache = pickle_cache or (
            get_pickle_cache_manager() if get_pickle_cache_manager else None
        )

        # Cache for company cadastral data.
        self._cache_cadastral: Optional[pd.DataFrame] = None

    def __enter__(self) -> "CVMClient":
        """Enters the context manager."""

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exits the context manager."""

        self.close()

    def _download_file(
        self,
        url: str,
        filename: str,
        description: str,
        *,
        timeout: int = 30,
        expiry_duration: timedelta = timedelta(hours=24),
    ) -> bytes:
        """Downloads a file with caching support.

        Args:
            url (str): URL to download.
            filename (str): Local filename for caching.
            description (str): Description for logging.
            timeout (int): Timeout for the download request.
            expiry_duration (timedelta): Duration after which the cache expires.

        Returns:
            bytes: Content of the downloaded file.
        """

        # Verify if cached version exists and is valid.
        if self.file_cache:
            content = self.file_cache.load_cache(
                "cvm", filename, expiry_duration=expiry_duration or self.CADASTRAL_CACHE_DURATION
            )
            if content:
                return content

        # If not cached, download from URL.
        logger.info(f"Downloading {description}...")
        response = self.http_client.get(url, timeout=timeout, stream=True)
        content = response.content  # Note: For very large files, consider chunked reading.

        if self.file_cache:
            self.file_cache.save_cache("cvm", filename, content)

        return content

    def _get_generic_report_data(
        self,
        cvm_code: str,
        year: int,
        consolidated: bool,
        base_url: str,
        file_prefix: str,
        source_tag: str,
    ) -> Dict[str, pd.DataFrame]:
        """Generic method to download and parse report data (ITR or DFP).

        Args:
            cvm_code (str): CVM code of the company.
            year (int): Year of the financial report.
            consolidated (bool): Whether to look for consolidated reports.
            base_url (str): Base URL for the report.
            file_prefix (str): Prefix for the filenames.
            source_tag (str): Tag indicating the source type (e.g., 'ITR', 'DFP').

        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping report types to DataFrames.

        Raises:
            FileNotFoundError: If the report for the given year is not found.
            Exception: For other unexpected errors during parsing.
        """

        filename = f"{file_prefix}_{year}.zip"
        url = f"{base_url}{filename}"

        try:
            response_content = self._download_file(
                url=url,
                filename=filename,
                description=f"{source_tag} data for the year {year}",
                timeout=self.REPORT_TIMEOUT,
            )
        except requests.exceptions.HTTPError as http_error:
            if http_error.response.status_code == 404:
                if source_tag == "DFP":
                    logger.warning(
                        f"DFP data for year {year} not found (404)."
                    )
                    return {}
                raise FileNotFoundError(
                    f"{source_tag} data for year {year} not found in CVM."
                ) from http_error
            raise

        # Search for CNPJ if not provided, as some reports may require it.
        target_cnpj = self.get_cnpj_by_cvm_code(cvm_code)

        # Delegate parsing to the specialized parser component.
        results = cvm_parser.parse_report_zip(
            content=response_content,
            cvm_code=cvm_code,
            target_cnpj=target_cnpj,
            year=year,
            report_types=cvm_settings.report_types,
            file_prefix=file_prefix,
            source_tag=source_tag,
            consolidated=consolidated,
        )

        if not results and source_tag == "ITR":
            logger.warning(
                f"No reports found for company {cvm_code} in year {year} ({source_tag})."
            )

        return results

    def _fetch_year_data(
        self, cvm_code: str, year: int
    ) -> List[Dict[str, pd.DataFrame]]:
        """Helper method to fetch both ITR and DFP data for a specific year.

        Extracted to a private method to improve testability and readability.

        Args:
            cvm_code (str): CVM code of the company.
            year (int): Year of the financial report.

        Returns:
            List[Dict[str, pd.DataFrame]]: List containing report data dictionaries.
        """

        # Initialize an empty list to store results for the year.
        results = []

        # Get the ITR Data
        try:
            itr_data = self.get_itr_data(cvm_code, year, consolidated=True)
            if itr_data:
                results.append(itr_data)
        except FileNotFoundError:
            logger.info(f"ITR {year} not found for company {cvm_code}.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error fetching ITR {year}: {e}")
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Unexpected error fetching ITR {year}: {e}")

        # Get the DFP Data
        try:
            dfp_data = self.get_dfp_data(cvm_code, year, consolidated=True)
            if dfp_data:
                results.append(dfp_data)
        except FileNotFoundError:
            logger.info(f"DFP {year} not found for company {cvm_code}.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error fetching DFP {year}: {e}")
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Unexpected error fetching DFP {year}: {e}")

        return results

    def _fetch_historical_financials(
        self, cvm_code: str, years_back: int = 3
    ) -> Dict[str, pd.DataFrame]:
        """Downloads and consolidates historical financial data (ITR and DFP) for the last N years.

        Args:
            cvm_code (str): CVM code of the company.
            years_back (int): Number of years of history to download. Defaults to 3.

        Returns:
            Dict[str, pd.DataFrame]: Consolidated financial data.
        """

        available_years = self.list_available_itr_years(fallback_years=years_back)
        target_years = available_years[:years_back]

        consolidated = {
            report_type: pd.DataFrame() for report_type in cvm_settings.report_types
        }

        # Parallel fetching of yearly data to speed up the process.
        # Uses MAX_CONCURRENT_DOWNLOADS to limit the number of threads.
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(target_years), self.MAX_CONCURRENT_DOWNLOADS)
        ) as executor:
            future_to_year = {
                executor.submit(self._fetch_year_data, cvm_code, year): year
                for year in target_years
            }

            for future in concurrent.futures.as_completed(future_to_year):
                year_results = future.result()
                for report_dict in year_results:
                    cvm_parser.append_report_data(consolidated, report_dict)

        return consolidated

    def close(self) -> None:
        """Closes the underlying HTTP client session."""

        if self.http_client:
            self.http_client.close()

    def get_cadastral_info(self) -> pd.DataFrame:
        """Downloads and returns the general registry of publicly traded companies.

        Useful for mapping CNPJ/Name to CVM Code. Uses Local Cache (24h).
        """

        if self._cache_cadastral is not None:
            return self._cache_cadastral

        response_content = self._download_file(
            url=cvm_settings.base_url_cad,
            filename=self.CVM_CADASTRAL_FILENAME,
            description="CVM company registry",
        )

        df = cvm_parser.parse_cadastral_csv(response_content)
        self._cache_cadastral = df

        return df

    def get_cvm_code_by_name(self, identifier: str) -> Optional[str]:
        """Searches for the CD_CVM using Ticker, Name, or partial name.

        Args:
            identifier (str): Ticker or Company Name.

        Returns:
            Optional[str]: Found CVM code or None.
        """

        # Load cadastral data.
        df = self.get_cadastral_info()

        return cvm_registry.resolve_cvm_code(df, identifier)

    def get_cnpj_by_cvm_code(self, cvm_code: str) -> Optional[str]:
        """Returns the CNPJ of the company given its CVM code.

        Args:
            cvm_code (str): CVM code of the company.

        Returns:
            Optional[str]: CNPJ if found, otherwise None.
        """

        df = self.get_cadastral_info()

        return cvm_registry.get_cnpj_by_cvm_code(df, cvm_code)

    def list_available_itr_years(self, fallback_years: int = 3) -> List[int]:
        """Lists available years for ITR reports on the CVM Open Data Portal.

        Args:
            fallback_years (int): Number of years to return in case of failure. Defaults to 3.

        Returns:
            List[int]: List of available years.
        """

        try:
            logger.info("Checking available ITR years on CVM...")
            response = self.http_client.get(cvm_settings.base_url_itr, timeout=self.LIST_YEARS_TIMEOUT)

            # Delega o parsing do HTML para o cvm_parser.
            sorted_years = cvm_parser.extract_years_from_html(response.content)

            logger.info(f"CVM years found: {sorted_years}")
            return sorted_years

        except Exception as e:
            logger.warning(
                f"Error listing CVM years automatically: {e}. Using fallback of {fallback_years} years."
            )
            return cvm_registry.get_fallback_years(fallback_years)

    def get_itr_data(
        self, cvm_code: str, year: int, *, consolidated: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """Downloads and processes ITR data.

        Args:
            cvm_code (str): CVM code of the company.
            year (int): Year of the financial report.
            consolidated (bool, optional): Whether to look for consolidated reports. Defaults to True.

        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping report types to DataFrames.
        """

        return self._get_generic_report_data(
            cvm_code=cvm_code,
            year=year,
            consolidated=consolidated,
            base_url=cvm_settings.base_url_itr,
            file_prefix="itr_cia_aberta",
            source_tag="ITR",
        )

    def get_dfp_data(
        self, cvm_code: str, year: int, *, consolidated: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """Downloads and processes DFP data.

        Args:
            cvm_code (str): CVM code of the company.
            year (int): Year of the financial report.
            consolidated (bool, optional): Whether to look for consolidated reports. Defaults to True.

        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping report types to DataFrames.
        """

        return self._get_generic_report_data(
            cvm_code=cvm_code,
            year=year,
            consolidated=consolidated,
            base_url=cvm_settings.base_url_dfp,
            file_prefix="dfp_cia_aberta",
            source_tag="DFP",
        )

    def get_consolidated_company_data(
        self, ticker: str, *, years_back: int = 3
    ) -> Dict[str, pd.DataFrame]:
        """Returns consolidated financial data for a company identified by ticker or name.

        Args:
            ticker (str): Ticker or company name.
            years_back (int): Number of years of history to download. Defaults to 3.

        Returns:
            Dict[str, pd.DataFrame]: Consolidated financial data.
        """

        # Resolve CVM Code
        cvm_code = self.get_cvm_code_by_name(ticker)
        if not cvm_code:
            raise ValueError(f"Empresa '{ticker}' não encontrada na CVM.")

        # Generate the cache filename using the centralized utility.
        cache_filename = format_cache_key(ticker, f"financials_{years_back}y.pkl")

        # If cached, return it directly.
        # File valid is 30 days.
        if self.pickle_cache:
            cached_data = self.pickle_cache.load_cache(
                "financials", cache_filename, expiry_duration=self.FINANCIAL_CACHE_DURATION
            )
            if cached_data:
                return cached_data

        logger.info(
            f"Generating new consolidated cache for {ticker} ({years_back} years)..."
        )

        # Fetch and Consolidate Data
        consolidated = self._fetch_historical_financials(
            cvm_code, years_back=years_back
        )

        # Save data to cache for future use.
        if self.pickle_cache:
            self.pickle_cache.save_cache("financials", cache_filename, consolidated)

        return consolidated
