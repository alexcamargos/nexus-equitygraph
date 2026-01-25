"""Helper functions for financial indicator tools (not exposed as LLM tools)."""

from functools import lru_cache
from typing import Any, List

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


def process_and_format_dre_for_year(dre_df: pd.DataFrame, year: str) -> List[str]:
    """Process and format the DRE (Income Statement) data for a specific year.

    Args:
        dre_df (pd.DataFrame): DataFrame containing the DRE data.
        year (str): The year for which the data should be processed.

    Returns:
        List[str]: List of formatted strings with the DRE data.
    """

    # Initialize output list for the year.
    output = []

    # Get DRE for the specified year.
    dre_year = dre_df[dre_df['DT_REFER'].astype(str).str.contains(year)].copy()

    if dre_year.empty:
        return output

    # Ensure date types
    dre_year['DT_REFER'] = pd.to_datetime(dre_year['DT_REFER'])
    if 'ORDEM_EXERC' in dre_year.columns:
        dre_year = dre_year[dre_year['ORDEM_EXERC'] == 'ÚLTIMO']

    if 'DT_INI_EXERC' in dre_year.columns:
        dre_year['DT_INI_EXERC'] = pd.to_datetime(dre_year['DT_INI_EXERC'])

    # Get the last quarter's DRE of that year (maximum reference).
    latest_reference_date = dre_year['DT_REFER'].max()
    latest_dre_records = dre_year[dre_year['DT_REFER'] == latest_reference_date]

    # Filter for Accumulated (Longest Period) per Account.
    # If duplicates exist (Quarter vs YTD), we want YTD (earliest start date).
    if not latest_dre_records.empty and 'DT_INI_EXERC' in latest_dre_records.columns:
        # Sort by start date (asc) -> Jan is earlier than July
        # dropping duplicates on CD_CONTA keeping first (Accumulated).
        latest_dre_records = latest_dre_records.sort_values('DT_INI_EXERC', ascending=True)
        latest_dre_records = latest_dre_records.drop_duplicates(subset=['CD_CONTA'], keep='first')

    lines = latest_dre_records[latest_dre_records['CD_CONTA'].isin(['3.01', '3.11', '3.99'])]

    if not lines.empty:
        output.append(f"DRE Resumo (Acumulado até {latest_reference_date.strftime('%m/%Y')}):")
        output.append(lines[['DS_CONTA', 'VL_CONTA']].to_string(index=False))

    return output


def process_and_format_bpp_for_year(mapper: Any, year: str) -> List[str]:
    """Process and format the BPP (Balance Sheet) data for a specific year.

    Args:
        mapper (Any): The account mapper object containing data.
        year (str): The year for which the data should be processed.

    Returns:
        List[str]: List of formatted strings with the BPP data.
    """

    # Initialize output list for the year.
    output = []

    # Get BPP DataFrame for the specified year.
    bpp_dataframe = mapper.data.get('BPP')

    if bpp_dataframe is None or bpp_dataframe.empty:
        return output

    # Filter Balance Sheet for the specified year.
    bpp_year = bpp_dataframe[bpp_dataframe['DT_REFER'].astype(str).str.contains(year)]

    if bpp_year.empty:
        return output

    # Get Equity for that lastest date,
    latest_reference_date = bpp_year['DT_REFER'].max()
    equity = mapper.get_equity(latest_reference_date)

    if equity:
        output.append(f"Patrimônio Líquido: {equity}")

    return output
