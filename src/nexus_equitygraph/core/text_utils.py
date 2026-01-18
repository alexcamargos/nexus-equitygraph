"""Text processing utilities for Nexus EquityGraph."""

import re
from typing import Optional

# Regular expressions, precompiled for performance, to clean company names.
RE_CLEAN_PUNCTUATION = re.compile(r"[\.\,\-]")
RE_REMOVE_CORP_SUFFIX = re.compile(r"\s+(S\s?A|S\/A|LTDA|HOLDING|PARTICIPACOES|PARTICIPAÇÕES)\b.*")


def normalize_company_name(name: Optional[str]) -> str:
    """Normalizes a company name by removing corporate suffixes and punctuation.

    Useful for matching across different data sources (CVM, YFinance, News).
    Ex: "WEG S.A." -> "WEG"

    Args:
        name (Optional[str]): Original company name.

    Returns:
        str: Normalized name in uppercase.
    """

    if not name:
        return ""

    clean = name.upper()
    clean = RE_CLEAN_PUNCTUATION.sub(" ", clean)
    clean = RE_REMOVE_CORP_SUFFIX.sub("", clean)

    # Remove extra spaces
    return " ".join(clean.split())


def format_cache_key(identifier: str, suffix: str) -> str:
    """Formats a string to be used as a safe filesystem cache key.

    Args:
        identifier (str): The base identifier (e.g., Ticker or Company Name).
        suffix (str): Suffix to append (e.g., 'financials_3y.pkl').

    Returns:
        str: A filesystem-safe filename.
    """

    safe_id = identifier.upper().replace(" ", "_").replace(".", "").replace("/", "")

    return f"{safe_id}_{suffix}"
