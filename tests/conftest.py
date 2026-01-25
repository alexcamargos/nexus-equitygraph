"""Global fixtures for Nexus EquityGraph tests."""

from datetime import datetime

import pandas as pd
import pytest


@pytest.fixture
def mock_cvm_data():
    """Creates a mock dictionary of DataFrames representing CVM consolidated data."""

    reporting_date_2023 = datetime(2023, 12, 31)
    reporting_date_2022 = datetime(2022, 12, 31)
    reporting_date_2018 = datetime(2018, 12, 31)  # For CAGR calculation (5 years back)

    # DRE (Income Statement)
    dre_data = [
        # 2023
        {
            "DT_REFER": reporting_date_2023,
            "CD_CVM": "004170",
            "CD_CONTA": "3.01",
            "DS_CONTA": "Receita de Venda",
            "VL_CONTA": 1000.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CVM": "004170",
            "CD_CONTA": "3.03",
            "DS_CONTA": "Resultado Bruto",
            "VL_CONTA": 500.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CVM": "004170",
            "CD_CONTA": "3.05",
            "DS_CONTA": "Resultado Antes do Resultado Financeiro e dos Tributos",
            "VL_CONTA": 300.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CVM": "004170",
            "CD_CONTA": "3.11",
            "DS_CONTA": "Lucro/Prejuízo Consolidado do Período",
            "VL_CONTA": 200.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        # 2022 (Comparison)
        {
            "DT_REFER": reporting_date_2022,
            "CD_CVM": "004170",
            "CD_CONTA": "3.01",
            "DS_CONTA": "Receita de Venda",
            "VL_CONTA": 900.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2022,
            "CD_CVM": "004170",
            "CD_CONTA": "3.03",
            "DS_CONTA": "Resultado Bruto",
            "VL_CONTA": 450.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2022,
            "CD_CVM": "004170",
            "CD_CONTA": "3.05",
            "DS_CONTA": "Resultado Antes",
            "VL_CONTA": 250.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2022,
            "CD_CVM": "004170",
            "CD_CONTA": "3.11",
            "DS_CONTA": "Lucro",
            "VL_CONTA": 180.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        # 2018 (CAGR Base)
        {
            "DT_REFER": reporting_date_2018,
            "CD_CVM": "004170",
            "CD_CONTA": "3.01",
            "DS_CONTA": "Receita de Venda",
            "VL_CONTA": 500.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2018,
            "CD_CVM": "004170",
            "CD_CONTA": "3.11",
            "DS_CONTA": "Lucro",
            "VL_CONTA": 100.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
    ]
    df_dre = pd.DataFrame(dre_data)

    # BPA (Assets)
    bpa_data = [
        {"DT_REFER": reporting_date_2023, "CD_CONTA": "1", "DS_CONTA": "Ativo Total", "VL_CONTA": 2000.0, "ORDEM_EXERC": "ÚLTIMO"},
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "1.01",
            "DS_CONTA": "Ativo Circulante",
            "VL_CONTA": 800.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "1.01.01",
            "DS_CONTA": "Caixa e Equivalentes",
            "VL_CONTA": 100.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        # 2022
        {"DT_REFER": reporting_date_2022, "CD_CONTA": "1", "DS_CONTA": "Ativo Total", "VL_CONTA": 1800.0, "ORDEM_EXERC": "ÚLTIMO"},
    ]
    df_bpa = pd.DataFrame(bpa_data)

    # BPP (Liabilities & Equity)
    bpp_data = [
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "2",
            "DS_CONTA": "Passivo Total",
            "VL_CONTA": 2000.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "2.01",
            "DS_CONTA": "Passivo Circulante",
            "VL_CONTA": 400.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "2.01.04",
            "DS_CONTA": "Empréstimos e Financiamentos (CP)",
            "VL_CONTA": 50.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "2.02.01",
            "DS_CONTA": "Empréstimos e Financiamentos (LP)",
            "VL_CONTA": 150.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "2.03",
            "DS_CONTA": "Patrimônio Líquido",
            "VL_CONTA": 1000.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        # 2022
        {
            "DT_REFER": reporting_date_2022,
            "CD_CONTA": "2.03",
            "DS_CONTA": "Patrimônio Líquido",
            "VL_CONTA": 900.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
    ]
    df_bpp = pd.DataFrame(bpp_data)

    # DFC (Cash Flow)
    dfc_data = [
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "6.01",
            "DS_CONTA": "Caixa Líquido Atividades Operacionais",
            "VL_CONTA": 250.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "6.02",
            "DS_CONTA": "Caixa Líquido Atividades de Investimento",
            "VL_CONTA": -50.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "",
            "DS_CONTA": "Dividendos Pagos",
            "VL_CONTA": -20.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
    ]
    df_dfc = pd.DataFrame(dfc_data)

    # DVA (Value Added)
    dva_data = [
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "1.03",
            "DS_CONTA": "Depreciação, Amortização e Exaustão",
            "VL_CONTA": -20.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {"DT_REFER": reporting_date_2023, "CD_CONTA": "7.02", "DS_CONTA": "Pessoal", "VL_CONTA": 50.0, "ORDEM_EXERC": "ÚLTIMO"},
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "7.03",
            "DS_CONTA": "Impostos, Taxas e Contribuições",
            "VL_CONTA": 30.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "7.04",
            "DS_CONTA": "Remuneração de Capitais de Terceiros",
            "VL_CONTA": 20.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
        {
            "DT_REFER": reporting_date_2023,
            "CD_CONTA": "7.05",
            "DS_CONTA": "Remuneração de Capitais Próprios",
            "VL_CONTA": 200.0,
            "ORDEM_EXERC": "ÚLTIMO",
        },
    ]
    df_dva = pd.DataFrame(dva_data)

    # Capital Composition
    cap_data = [{"DT_REFER": reporting_date_2023, "QT_TOTAL": 1000}]
    df_cap = pd.DataFrame(cap_data)

    # Auditor Report
    parecer_data = [
        {
            "DT_REFER": reporting_date_2023,
            "NM_AUDITOR": "Auditor Global Teste",
            "DS_OPINIAO": "Sem ressalvas",
            "TP_RELAT_AUD": "Sem ressalvas",
        }
    ]
    df_parecer = pd.DataFrame(parecer_data)

    return {
        "DRE": df_dre,
        "BPA": df_bpa,
        "BPP": df_bpp,
        "DFC_MD": df_dfc,
        "DVA": df_dva,
        "composicao_capital": df_cap,
        "parecer": df_parecer,
    }


@pytest.fixture
def mock_company_profile():
    """Creates a mock dictionary for company profile data."""

    return {
        "company_name": "Nexus Tech S.A.",
        "trading_name": "Nexus",
        "cnpj": "12.345.678/0001-90",
        "activity": "Tecnologia da Informação",
        "registration_date": "01/01/2010",
        "founding_date": "01/01/2005",
        "city": "São Paulo",
        "state": "SP",
        "status": "Ativo",
        "auditor": "Auditor Global Teste",
    }
