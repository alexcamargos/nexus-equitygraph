"""Helper functions for financial indicator tools (not exposed as LLM tools)."""

from functools import lru_cache
from typing import Any

import pandas as pd

from nexus_equitygraph.services.cvm_mapper import CVMAccountMapper
from nexus_equitygraph.services.cvm_client import CVMClient


def _get_row_value(row: pd.Series, key: str, not_found_value: str = "N/A") -> str:
    """Safely extracts a string value from a DataFrame row.

    Args:
        row(pd.Series): DataFrame row.
        key(str): Key to extract.
        not_found_value(str): Default value to return if key is not found.

    Returns:
        str: Extracted value or default.
    """

    key_value = row.get(key, not_found_value)

    return str(key_value) if pd.notna(key_value) else not_found_value


@lru_cache(maxsize=1)
def get_account_mapper(ticker: str) -> CVMAccountMapper:
    """Factory function for CVMAccountMapper with caching by ticker."""

    return CVMAccountMapper(get_consolidated_data(ticker) or {})


@lru_cache(maxsize=1)
def get_cvm_client() -> CVMClient:
    """Factory function for CVMClient with singleton caching."""

    return CVMClient()


@lru_cache(maxsize=1)
def get_consolidated_data(ticker: str) -> dict[str, pd.DataFrame]:
    """Retrieves consolidated company data (cached) using CVMClient.

    This function uses caching to avoid redundant data fetches for the same ticker.

    Args:
        ticker(str): Company ticker symbol.

    Returns:
        Dictionary with consolidated company data.
    """

    return get_cvm_client().get_consolidated_company_data(ticker)


def build_metadata(sources: list[str], periods: list[Any]) -> str:
    """Generates a declarative metadata footer for reports.

    Args:
        sources(list[str]): List of data sources.
        periods(list[Any]): List of reference periods (dates or strings).

    Returns:
        str: Formatted metadata string.
    """

    sources_string = ", ".join(sources)

    formatted_dates = []
    for period in periods:
        if hasattr(period, "strftime"):
            formatted_dates.append(period.strftime("%d/%m/%Y"))
        else:
            formatted_dates.append(str(period))

    formatted_dates_string = ", ".join(formatted_dates)

    return (
        f"\n\n> **Metadados:**\n> *   **Fontes:** {sources_string}\n> *   **Ref. Temporal:** {formatted_dates_string}"
    )


def get_company_profile_data(ticker: str) -> dict[str, Any]:
    """Helper function to get raw profile data as a dictionary.

    Args:
        ticker(str): Company ticker symbol.

    Returns:
        Dictionary with company profile data.
    """

    cvm_code = get_cvm_client().get_cvm_code_by_name(ticker)
    if not cvm_code:
        return {"error": f"Empresa {ticker} não encontrada no cadastro CVM."}

    company_cadastral_data = get_cvm_client().get_cadastral_info()
    target_code = str(int(cvm_code)).zfill(6)

    # Filtering
    cadastral_code_mask = company_cadastral_data["CD_CVM"].astype(str).str.zfill(6) == target_code
    if not cadastral_code_mask.any():
        cadastral_code_mask = company_cadastral_data["CD_CVM"].astype(str) == str(cvm_code)

    if not cadastral_code_mask.any():
        return {"error": f"Código CVM {cvm_code} não encontrado no processamento cadastral."}

    row = company_cadastral_data.loc[cadastral_code_mask].iloc[0]

    company_profile = {
        "company_name": _get_row_value(row, "DENOM_SOCIAL"),
        "trading_name": _get_row_value(row, "DENOM_COMERC"),
        "cnpj": _get_row_value(row, "CNPJ_CIA"),
        "activity": _get_row_value(row, "SETOR_ATIV"),
        "registration_date": _get_row_value(row, "DT_REG"),
        "founding_date": _get_row_value(row, "DT_CONST"),
        "city": _get_row_value(row, "MUN"),
        "state": _get_row_value(row, "UF"),
        "status": _get_row_value(row, "SIT"),
    }

    if "AUDITOR" in company_cadastral_data.columns:
        company_profile["auditor"] = _get_row_value(row, "AUDITOR")

    return company_profile


def format_percentage_currency(label: str, value: float, total: float) -> str:
    """Format a distribution line with percentage and currency.

    Args:
        label(str): Human-readable label for the line (e.g., 'Pessoal (Salários)').
        value(float): Numeric value for the item.
        total(float): Total against which percentage is calculated.

    Returns:
        Formatted string like "Label: 12.3% (R$ 1.234)".
    """

    percentage_value = (value / total) * 100 if total else 0.0

    return f"{label}: {percentage_value:.1f}% (R$ {value:,.0f})"
