"""Financial statement tools for the Fundamentalist Agent."""

from langchain_core.tools import tool

from nexus_equitygraph.core.exceptions import handle_indicator_exceptions

from .helpers import (
    build_metadata,
    get_account_mapper,
    process_and_format_bpp_for_year,
    process_and_format_dre_for_year,
)


@tool
@handle_indicator_exceptions("demonstrações financeiras")
def get_financial_statements(ticker: str, years_depth: int = 3) -> str:
    """Process and return historical financial statements for a given ticker.

    Retrieve and format historical financial statements (DRE and BPP) for a specified stock ticker.
    The function utilizes cached data to improve performance and provides a summary of financial metrics
    for the most recent years available.

    Args:
        ticker (str): Stock ticker symbol.
        years_depth (int, optional): Number of years to retrieve. Defaults to 3.

    Returns:
        str: Formatted financial statements.
    """

    # Grants minimum depth of 1 year to avoid empty responses and ensure meaningful output.
    years_depth = max(1, years_depth)

    mapper = get_account_mapper(ticker)
    data = mapper.data

    if "DRE" not in data or data["DRE"].empty:
        return "Dados DRE não encontrados."

    years_found = sorted(data['DRE']['DT_REFER'].astype(str).str[:4].unique().tolist(), reverse=True)
    cvm_code_identifier = data['DRE']['CD_CVM'].iloc[0] if not data['DRE'].empty else "?"

    output = [f"RELATÓRIO FINANCEIRO HISTÓRICO: {ticker} (CVM: {cvm_code_identifier})"]
    output.append(f"Anos Disponíveis no Cache: {years_found}\n")

    if not years_found:
        return "Nenhum dado financeiro encontrado no cache consolidado."

    # Limit to the requested number of years.
    target_years = years_found[:years_depth]
    for year in target_years:
        output.append(f"--- Exercício {year} ---")

        # Process and format the DRE (Income Statement)
        output.extend(process_and_format_dre_for_year(data['DRE'], year))

        # Process and format the BPP (Balance Sheet)
        if 'BPP' in data:
            output.extend(process_and_format_bpp_for_year(mapper, year))

        output.append("")

    footer = build_metadata(["CVM (ITR/DFP)"], target_years)

    return "\n".join(output) + footer
