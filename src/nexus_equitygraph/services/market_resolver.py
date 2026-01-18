"""Module to resolve company names from market tickers using YFinance."""

import re
from typing import Optional

import requests
import yfinance as yf
from loguru import logger

from nexus_equitygraph.core.text_utils import normalize_company_name


def resolve_name_from_ticker(identifier: str | None) -> Optional[str]:
    """Attempts to resolve a Ticker to a Company Name using YFinance.

    Example: "WEGE3" -> "WEG"

    Args:
        identifier (str | None): The ticker or identifier to resolve.

    Returns:
        Optional[str]: The normalized company name if found, otherwise None.
    
    Raises:
        requests.exceptions.RequestException: For network-related errors.
        requests.exceptions.Timeout: If the request times out.
        requests.exceptions.HTTPError: For HTTP errors (e.g., rate limiting).
        Exception: For other unexpected errors.
    """

    # Validates identifier input for empty or null values.
    if not identifier or not isinstance(identifier, str):
        return None

    clean_id = identifier.upper().strip()

    # Regex to identify if it looks like a B3 ticker (4 letters + digit).
    if not re.match(r"^[A-Z]{4}\d{1,2}(\.SA)?$", clean_id):
        return None

    # Remove .SA suffix if present for YFinance (the Brazilian standard is .SA)
    yf_ticker = clean_id if ".SA" in clean_id else f"{clean_id}.SA"

    try:
        stock = yf.Ticker(yf_ticker)
        info = stock.info

        # Tries longName or shortName
        resolved_company_name = info.get("longName") or info.get("shortName")

        if resolved_company_name:
            logger.debug(f"YFinance identified: '{resolved_company_name}' for ticker {clean_id}")
            # Normalizes company names.
            # Example: "WEG S.A." -> "WEG"
            return normalize_company_name(resolved_company_name)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error:
        logger.warning(f"Network issue resolving ticker {clean_id} on YFinance: {error}")
    except requests.exceptions.HTTPError as error:
        logger.warning(f"HTTP error (possible rate limiting) for ticker {clean_id}: {error}")
    except Exception as error:  # pylint: disable=broad-except
        logger.error(f"Unexpected error resolving ticker {clean_id} on YFinance: {error}")

    return None
