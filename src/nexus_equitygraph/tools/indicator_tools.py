"""Financial indicator tools for the Fundamentalist Agent."""

from datetime import datetime

import pandas as pd
from langchain_core.tools import tool

from nexus_equitygraph.core.exceptions import handle_indicator_exceptions

from .helpers import (
    build_metadata,
    format_percentage_currency,
    get_account_mapper,
    get_company_profile_data,
    get_consolidated_data,
)


@tool
@handle_indicator_exceptions("perfil")
def get_company_profile(ticker: str) -> str:
    """Returns company registration data (CNPJ, Sector, Activity, etc.).

    Fetches and formats the company's registration profile data from CVM.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        str: Formatted string with company profile data.
    """

    data = get_company_profile_data(ticker)
    if "error" in data:
        return str(data["error"])

    profile = [f"--- Dados da Companhia ({ticker}) ---"]
    profile.append(f"Nome Empresarial: {data.get('company_name', 'N/A')}")
    profile.append(f"Nome Pregão: {data.get('trading_name', 'N/A')}")
    profile.append(f"CNPJ: {data.get('cnpj', 'N/A')}")
    profile.append(f"Atividade (CVM): {data.get('activity', 'N/A')}")
    profile.append(f"Início Negociação/Registro: {data.get('registration_date', 'N/A')}")
    profile.append(f"Fundação: {data.get('founding_date', 'N/A')}")
    profile.append(f"Sede: {data.get('city', 'N/A')} / {data.get('state', 'N/A')}")
    profile.append(f"Situação: {data.get('status', 'N/A')}")

    if "auditor" in data:
        profile.append(f"Auditor (Cadastro): {data['auditor']}")

    footer = build_metadata(["CVM (Cadastral)"], ["Atual"])

    return "\n".join(profile) + footer


@tool
@handle_indicator_exceptions("valuation")
def calculate_valuation_indicators(ticker: str, current_price: float) -> str:
    """Calculates Valuation indicators (P/E, P/B, EV/EBITDA, etc.).

    Given a company ticker and its current stock price, this tool computes various
    valuation metrics using the latest financial data from CVM.
    It returns a formatted string with the results.

    Args:
        ticker (str): The company ticker (e.g., PETR4).
        current_price (float): The current stock price.

    Returns:
        str: Formatted string with valuation metrics.
    """

    mapper = get_account_mapper(ticker)

    # Key financial figures
    shares = mapper.share_count
    equity = mapper.get_equity()
    net_income = mapper.get_net_income()
    ebitda = mapper.get_ebitda()
    net_debt = mapper.get_gross_debt() - mapper.get_cash_and_equivalents()
    divs = mapper.get_dividends_paid()

    # Free Cash Flow (Simplified: OCF + Capex)
    # Capex is usually negative (outflow), so we add it.
    free_cash_flow = mapper.get_operating_cash_flow() + mapper.get_capex()

    results = [f"--- Valuation (Dados CVM {datetime.now().year} + Preço R$ {current_price:.2f}) ---"]

    if shares > 0:
        market_cap = current_price * shares
        lpa = net_income / shares
        vpa = equity / shares

        market_cap_string = f"R$ {market_cap:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        results.append(f"Market Cap: {market_cap_string}")
        results.append(f"Total Ações: {shares:,}".replace(",", "."))

        if lpa != 0:
            pl = current_price / lpa
            results.append(f"P/L: {pl:.2f}")

        if vpa > 0:
            pvp = current_price / vpa
            results.append(f"P/VP: {pvp:.2f}")

        if market_cap > 0:
            dy = (divs / market_cap) * 100
            results.append(f"Dividend Yield (LTM): {dy:.2f}% (Pago: {divs:,.0f})")

        if free_cash_flow != 0 and market_cap > 0:
            price_to_free_cash_flow = market_cap / free_cash_flow
            results.append(f"P/FCF: {price_to_free_cash_flow:.2f}")
            results.append(f"  (FCF Estimado: {free_cash_flow:,.0f})")

        enterprise_value = market_cap + net_debt
        if ebitda > 0:
            ev_ebitda = enterprise_value / ebitda
            results.append(f"EV/EBITDA: {ev_ebitda:.2f}")
    else:
        results.append("AVISO: Número de ações não encontrado na base CVM.")

    reference_date = mapper.data["DRE"]["DT_REFER"].max() if "DRE" in mapper.data else "N/A"
    footer = build_metadata(["Mercado", "Composição Capital", "DRE", "Balanço", "DFC"], [reference_date])

    return "\n".join(results) + footer


@tool
@handle_indicator_exceptions("eficiência")
def calculate_efficiency_indicators(ticker: str) -> str:
    """Calculates efficiency margins with historical comparison.

    Calculates gross, EBIT, and net margins over multiple periods
    and returns a formatted markdown table with the results.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        str: Formatted string with efficiency metrics.
    """

    mapper = get_account_mapper(ticker)

    periods = mapper.get_comparison_dates()
    if not periods:
        return "Dados insuficientes."

    headers = ["Indicador"] + [period_info[0] for period_info in periods]
    md_table = f"| {' | '.join(headers)} |\n"
    md_table += f"| {' | '.join(['---'] * len(headers))} |\n"

    rows = {"M. Bruta": [], "M. EBIT": [], "M. Liq": []}

    for _, reporting_date in periods:
        revenue_amount = mapper.get_revenue(reporting_date)
        gross_profit_amount = mapper.get_gross_profit(reporting_date)
        ebit = mapper.get_ebit(reporting_date)
        net_income = mapper.get_net_income(reporting_date)

        rows["M. Bruta"].append(f"{(gross_profit_amount / revenue_amount * 100):.2f}%" if revenue_amount else "0.00%")
        rows["M. EBIT"].append(f"{(ebit / revenue_amount * 100):.2f}%" if revenue_amount else "0.00%")
        rows["M. Liq"].append(f"{(net_income / revenue_amount * 100):.2f}%" if revenue_amount else "0.00%")

    md_table += f"| **Margem Bruta** | {' | '.join(rows['M. Bruta'])} |\n"
    md_table += f"| **Margem EBIT** | {' | '.join(rows['M. EBIT'])} |\n"
    md_table += f"| **Margem Líquida** | {' | '.join(rows['M. Liq'])} |\n"

    footer = build_metadata(["DRE"], [period_info[1] for period_info in periods])

    return f"\n### Eficiência (Margens)\n{md_table}{footer}"


@tool
@handle_indicator_exceptions("dívida")
def calculate_debt_indicators(ticker: str) -> str:
    """Calculates debt and solvency indicators with historical comparison.

    Calculates Debt/EBITDA and Current Ratio over multiple periods
    and returns a formatted markdown table with the results.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        str: Formatted string with debt and solvency metrics.
    """

    mapper = get_account_mapper(ticker)

    periods = mapper.get_comparison_dates()
    if not periods:
        return "Dados insuficientes."

    headers = ["Indicador"] + [period_info[0] for period_info in periods]
    md_table = f"| {' | '.join(headers)} |\n"
    md_table += f"| {' | '.join(['---'] * len(headers))} |\n"

    rows = {"DL/EBITDA": [], "Liq Corr": []}

    for _, reporting_date in periods:
        gross_debt = mapper.get_gross_debt(reporting_date)
        cash = mapper.get_cash_and_equivalents(reporting_date)
        net_debt = gross_debt - cash
        ebitda = mapper.get_ebitda(reporting_date)

        debt_to_ebitda_ratio = (net_debt / ebitda) if ebitda and ebitda != 0 else 0.0
        rows["DL/EBITDA"].append(f"{debt_to_ebitda_ratio:.2f}x")

        current_assets = mapper.get_current_assets(reporting_date)
        current_liabilities = mapper.get_current_liabilities(reporting_date)
        current_liquidity = (
            (current_assets / current_liabilities) if current_liabilities and current_liabilities != 0 else 0.0
        )
        rows["Liq Corr"].append(f"{current_liquidity:.2f}")

    md_table += f"| **Dívida Líq / EBITDA** | {' | '.join(rows['DL/EBITDA'])} |\n"
    md_table += f"| **Liquidez Corrente** | {' | '.join(rows['Liq Corr'])} |\n"

    footer = build_metadata(["Balanço Patrimonial", "DRE"], [period_info[1] for period_info in periods])

    return f"\n### Endividamento e Solvência\n{md_table}{footer}"


@tool
@handle_indicator_exceptions("rentabilidade")
def calculate_rentability_indicators(ticker: str) -> str:
    """Calculates rentability indicators (ROE, ROA) with historical comparison.

    Calculates ROE and ROA over multiple periods and returns a formatted markdown table with the results.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        str: Formatted string with rentability metrics.
    """

    mapper = get_account_mapper(ticker)

    periods = mapper.get_comparison_dates()
    if not periods:
        return "Dados insuficientes."

    headers = ["Indicador"] + [period_info[0] for period_info in periods]
    md_table = f"| {' | '.join(headers)} |\n"
    md_table += f"| {' | '.join(['---'] * len(headers))} |\n"

    rows = {"ROE": [], "ROA": []}

    for _, reporting_date in periods:
        net_income = mapper.get_net_income(reporting_date)
        equity = mapper.get_equity(reporting_date)
        roe = (net_income / equity * 100) if equity and equity != 0 else 0.0
        rows["ROE"].append(f"{roe:.2f}%")

        assets = mapper.get_total_assets(reporting_date)
        roa = (net_income / assets * 100) if assets and assets != 0 else 0.0
        rows["ROA"].append(f"{roa:.2f}%")

    md_table += f"| **ROE** | {' | '.join(rows['ROE'])} |\n"
    md_table += f"| **ROA** | {' | '.join(rows['ROA'])} |\n"

    footer = build_metadata(["DRE", "Balanço Patrimonial"], [p[1] for p in periods])

    return f"\n### Rentabilidade (Evolução)\n{md_table}{footer}"


@tool
@handle_indicator_exceptions("crescimento")
def calculate_growth_indicators(ticker: str) -> str:
    """Calculates CAGR for Revenue and Net Income (5 years).

    Calculates the Compound Annual Growth Rate (CAGR) for Revenue and Net Income
    over the last 5 years using CVM data. Returns a formatted string with the results.

    Args:
        ticker (str): The company ticker (e.g., PETR4).
    Returns:
        str: Formatted string with CAGR metrics.
    """

    data = get_consolidated_data(ticker)
    if "DRE" not in data:
        return "Dados DRE insuficientes."

    dre = data["DRE"]
    dates = pd.to_datetime(dre["DT_REFER"], errors="coerce")
    available_years = sorted(dates.dt.year.unique(), reverse=True)

    if not available_years:
        return "Sem dados de ano."

    current_year = available_years[0]
    start_year = available_years[-1]

    if current_year == start_year:
        return "Série histórica insuficiente (apenas 1 ano)."

    # Determine reference dates for LTM calculation.
    # We use the max date available for the current year,
    # and try to find the same date 5 years ago for the start year.
    max_date = dates.max()
    try:
        start_date_target = max_date.replace(year=start_year)
    except ValueError:
        start_date_target = max_date.replace(year=start_year, day=28)

    mapper = get_account_mapper(ticker)

    # Calculate CAGR for Revenue
    current_revenue = mapper.get_revenue(reference_date=max_date)
    initial_revenue = mapper.get_revenue(reference_date=start_date_target)

    years = current_year - start_year
    results = [f"--- Crescimento (CAGR {years} Anos) ---"]

    if initial_revenue > 0 and current_revenue > 0:
        cagr_revenue = ((current_revenue / initial_revenue) ** (1 / years) - 1) * 100
        results.append(f"CAGR Receitas: {cagr_revenue:.2f}%")

    # Calculate CAGR for Net Income
    current_net_income = mapper.get_net_income(reference_date=max_date)
    initial_net_income = mapper.get_net_income(reference_date=start_date_target)

    if initial_net_income > 0 and current_net_income > 0:
        cagr_net_income = ((current_net_income / initial_net_income) ** (1 / years) - 1) * 100
        results.append(f"CAGR Lucros: {cagr_net_income:.2f}%")
    elif initial_net_income < 0 < current_net_income:
        results.append("CAGR Lucros: Reversão de Prejuízo (N/A matematicamente)")

    footer = build_metadata(["DRE"], [f"{start_year}", f"{current_year}"])

    return "\n".join(results) + footer


@tool
@handle_indicator_exceptions("evolução financeira")
def get_financial_evolution(ticker: str) -> str:
    """Returns quarterly evolution of main indicators (Revenue, Net Income, EBIT).

    Provides a quarterly summary of key financial indicators
    such as Revenue, Net Income, and EBIT from the DRE statement.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        str: Formatted string with quarterly evolution.
    """

    mapper = get_account_mapper(ticker)
    if "DRE" not in mapper.data:
        return "Dados DRE não disponíveis para evolução."

    dre = mapper.data["DRE"]
    dates = sorted(dre["DT_REFER"].unique())

    summary = [f"--- Evolução Trimestral (Acumulado Ano) - {ticker} ---"]
    header = f"{'Data':<12} | {'Receita (Mil)':<15} | {'Lucro Liq (Mil)':<15} | {'EBIT (Mil)':<15}"
    summary.append(header)
    summary.append("-" * len(header))

    for date in dates:
        revenue = mapper.get_raw_value("DRE", "3.01", "Receita", date)
        net_income = mapper.get_raw_value("DRE", "3.11", "Lucro", date)
        ebit = mapper.get_raw_value("DRE", "3.05", "Resultado Antes", date)

        summary.append(f"{date:<12} | {revenue:<15,.0f} | {net_income:<15,.0f} | {ebit:<15,.0f}")

    footer = build_metadata(["DRE"], dates)

    return "\n".join(summary) + footer


@tool
@handle_indicator_exceptions("auditoria")
def get_auditor_info(ticker: str) -> str:
    """Returns information about the auditor and their opinion.

    Fetches the latest auditor name and opinion from the company's
    audit reports. If unavailable, falls back to CVM cadastral data.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        str: Formatted string with auditor info.
    """

    data = get_consolidated_data(ticker)

    # Logic to extract auditor info from 'parecer' dataframe.
    auditor_name = "N/A"
    opinion = "N/A"

    # Try to get from audit reports first.
    if "parecer" in data and not data["parecer"].empty:
        df = data["parecer"]
        # Filter valid rows
        mask_valid = df["TP_RELAT_AUD"].notna() | df["DS_OPINIAO"].notna()
        valid_rows = df[mask_valid].sort_values(by="DT_REFER", ascending=False)

        if not valid_rows.empty:
            latest = valid_rows.iloc[0]
            opinion = latest.get("TP_RELAT_AUD") or latest.get("DS_OPINIAO") or "N/A"
            auditor_name = latest.get("NM_AUDITOR") or "Info. não estruturada"

    sources = ["Parecer do Auditor"]

    # Fallback to Cadastral info if needed.
    if auditor_name in ["Info. não estruturada", "N/A", ""] or pd.isna(auditor_name):
        profile_data = get_company_profile_data(ticker)
        if "error" not in profile_data:
            registered_auditor = profile_data.get("auditor")
            if registered_auditor and registered_auditor != "N/A":
                auditor_name = f"{registered_auditor} (Cadastro CVM)"
                sources.append("CVM (Cadastral)")

    reference_date = data["parecer"]["DT_REFER"].max() if "parecer" in data else "N/A"
    footer = build_metadata(sources, [reference_date])

    return f"Auditor: {auditor_name}\nOpinião: {opinion}{footer}"


@tool
@handle_indicator_exceptions("DVA")
def calculate_wealth_distribution(ticker: str) -> str:
    """Analyzes the DVA (Value Added Statement) to show wealth distribution.

    Analyzes the DVA statement to compute and display the
    distribution of wealth among different stakeholders.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        str: Formatted string with wealth distribution.
    """

    mapper = get_account_mapper(ticker)

    personnel_compensation = mapper.dva_personnel()
    government_taxes = mapper.dva_taxes()
    third_party_lenders = mapper.dva_lenders()
    shareholders_profit = mapper.dva_shareholders()

    total_dist = personnel_compensation + government_taxes + third_party_lenders + shareholders_profit

    if total_dist == 0:
        return "DVA zerada ou indisponível."

    formatted_distribution_output = ["--- Distribuição de Riqueza (DVA) ---"]
    formatted_distribution_output.append(
        format_percentage_currency("Pessoal (Salários)", personnel_compensation, total_dist)
    )
    formatted_distribution_output.append(format_percentage_currency("Governo (Impostos)", government_taxes, total_dist))
    formatted_distribution_output.append(
        format_percentage_currency("Terceiros (Juros)", third_party_lenders, total_dist)
    )
    formatted_distribution_output.append(
        format_percentage_currency("Acionistas (Lucro)", shareholders_profit, total_dist)
    )

    reference_date = mapper.data["DVA"]["DT_REFER"].max() if "DVA" in mapper.data else "N/A"
    footer = build_metadata(["DVA"], [reference_date])

    return "\n".join(formatted_distribution_output) + footer
