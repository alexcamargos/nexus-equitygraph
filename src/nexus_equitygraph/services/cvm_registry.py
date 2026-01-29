"""Service for searching and mapping data within the CVM Cadastral Registry."""

from datetime import datetime
from typing import Any, List, Optional

import pandas as pd
from loguru import logger

from nexus_equitygraph.core.text_utils import normalize_company_name
from nexus_equitygraph.services.market_resolver import resolve_name_from_ticker


def get_fallback_years(count: int) -> List[int]:
    """Generates a list of recent years as a fallback when the CVM portal is unreachable.

    Args:
        count (int): Number of years to generate.
    """

    current_year = datetime.now().year

    return list(range(current_year, current_year - count, -1))


def find_cvm_code_in_df(df: pd.DataFrame, term: str) -> Optional[str]:
    """Helper to search for a term in the cadastral DataFrame.
    
    Prioritizes exact matches and shorter names (Heuristic for Holdings).
    
    Args:
        df (pd.DataFrame): The cadastral DataFrame.
        term (str): The term to search for.
        
    Returns:
        Optional[str]: The found CVM Code if found, otherwise None.
    """
    mask = df["DENOM_SOCIAL"].str.contains(term, case=False, na=False)
    matches = df[mask]

    if matches.empty:
        return None

    # Heuristic: Shorter name = Holding/Main (Avoids "WEG EQUIPAMENTOS...")
    matches = matches.sort_values(by="DENOM_SOCIAL", key=lambda x: x.str.len())

    found_name = matches.iloc[0]["DENOM_SOCIAL"]
    found_code = matches.iloc[0]["CD_CVM"]

    logger.info(f"Company identified: '{found_name}' (CVM: {found_code})")

    return str(found_code)


def get_cnpj_by_cvm_code(df: pd.DataFrame, cvm_code: Any) -> Optional[str]:
    """Maps a CVM Code to a CNPJ using the provided cadastral DataFrame.
    
    Handles type conversion and padding as needed.
    
    Args:
        df (pd.DataFrame): The cadastral DataFrame.
        cvm_code (str): The CVM code to map.
        
    Returns:
        Optional[str]: The corresponding CNPJ if found, otherwise None.
    
    Raises:
        ValueError: If the provided CVM code cannot be converted to an integer.
        TypeError: If the provided CVM code is not a string or number.
    """

    try:
        target = str(int(cvm_code))
    except (ValueError, TypeError):
        logger.warning(f"Invalid CVM code: {cvm_code}")
        return None

    # Try direct match
    mask = df["CD_CVM"].astype(str) == target
    if not mask.any():
        # Try padded (CVM standard is often 6 digits)
        mask = df["CD_CVM"].astype(str).str.zfill(6) == target.zfill(6)

    if mask.any():
        return df.loc[mask, "CNPJ_CIA"].iloc[0]

    return None


def resolve_cvm_code(df: pd.DataFrame, identifier: str) -> Optional[str]:
    """Orchestrates the resolution of a CVM Code from various input types.

    Strategy:
    1. Direct search (Name).
    2. Ticker resolution (via Market Resolver).
    3. Normalized name search.
    
    Args:
        df (pd.DataFrame): The cadastral DataFrame.
        identifier (str): The input identifier (Name or Ticker).
    
    Returns:
        Optional[str]: The resolved CVM Code if found, otherwise None.
    """

    # Try direct search first, prioritizing exact matches.
    res = find_cvm_code_in_df(df, identifier)
    if res:
        return res

    # Try ticker resolution via YFinance, if applicable.
    name_from_ticker = resolve_name_from_ticker(identifier)
    if name_from_ticker:
        res = find_cvm_code_in_df(df, name_from_ticker)
        if res:
            return res

    # Try normalization search as a last resort.
    # Example: "WEG S.A." -> "WEG"
    norm_input = normalize_company_name(identifier)
    if norm_input != identifier and len(norm_input) >= 2:
        res = find_cvm_code_in_df(df, norm_input)
        if res:
            return res

    # Try Ticker Root Heuristic (e.g. CEMIG4 -> CEMIG)
    # Extracts the first 4 letters if the identifier looks like a ticker.
    if len(identifier) >= 4 and identifier[:4].isalpha():
        ticker_root = identifier[:4]
        # Avoid searching for very common/short roots if they might match too many things, 
        # but 4 chars is usually safe for CVM list.
        res = find_cvm_code_in_df(df, ticker_root)
        if res:
            return res

    return None
