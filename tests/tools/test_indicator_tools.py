"""Tests for the financial indicator tools using global mocks."""

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from nexus_equitygraph.services.cvm_mapper import CVMAccountMapper
from nexus_equitygraph.tools.indicator_tools import (
    calculate_debt_indicators,
    calculate_efficiency_indicators,
    calculate_growth_indicators,
    calculate_rentability_indicators,
    calculate_valuation_indicators,
    calculate_wealth_distribution,
    get_auditor_info,
    get_company_profile,
    get_financial_evolution,
)


class TestIndicatorTools:
    """Test suite for financial indicator tools."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_cvm_data, mock_company_profile):
        """Setup common test data from global fixtures."""

        self.mock_data = mock_cvm_data
        self.mock_profile = mock_company_profile
        self.ticker = "TEST3"

    @pytest.fixture
    def mock_mapper(self, mock_cvm_data):
        """Fixture to create a CVMAccountMapper instance with mock data."""

        return CVMAccountMapper(mock_cvm_data)

    @pytest.fixture
    def empty_mapper(self):
        """Fixture to create an empty CVMAccountMapper instance."""

        return CVMAccountMapper({})

    def test_get_company_profile_success(self):
        """Test retrieving company profile with valid data."""

        # Arrange: Mock the data retrieval function to return the mock profile.
        with patch("nexus_equitygraph.tools.indicator_tools.get_company_profile_data", return_value=self.mock_profile):

            # Act: Invoke the function to get the company profile.
            result = get_company_profile.invoke({"ticker": self.ticker})

            # Assert: Check if the returned profile contains expected information.
            assert "Nexus Tech S.A." in result
            assert "12.345.678/0001-90" in result
            assert "Metadados" in result

    def test_calculate_valuation_indicators_success(self, mock_mapper):
        """Test valuation calculations (P/E, EV/EBITDA, etc.)."""

        # Act & Assert: Calculate valuation indicators using the mock data.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper):

            # Act: Calculate valuation indicators using the mock data.
            result = calculate_valuation_indicators.invoke({"ticker": self.ticker, "current_price": 10.0})

            # Assert: Verify the calculated valuation indicators.
            assert "Market Cap: R$ 10.000,00" in result
            assert "P/L: 50.00" in result
            assert "P/VP: 10.00" in result
            assert "EV/EBITDA: 31.56" in result

    def test_calculate_efficiency_indicators_success(self, mock_mapper):
        """Test efficiency margins (Gross, EBIT, Net)."""

        # Act & Assert: Calculate efficiency indicators using the mock data.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper):

            # Act: Calculate efficiency indicators using the mock data.
            result = calculate_efficiency_indicators.invoke({"ticker": self.ticker})

            # Assert: Verify the calculated efficiency margins.
            assert "50.00%" in result  # Gross Margin
            assert "30.00%" in result  # EBIT Margin
            assert "20.00%" in result  # Net Margin
            assert "Eficiência (Margens)" in result

    def test_calculate_debt_indicators_success(self, mock_mapper):
        """Test debt and liquidity indicators."""

        # Act & Assert: Calculate debt indicators using the mock data.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper):

            # Act: Calculate debt indicators using the mock data.
            result = calculate_debt_indicators.invoke({"ticker": self.ticker})

            # Assert: Verify the calculated debt and liquidity indicators.
            assert "0.31x" in result
            assert "2.00" in result
            assert "Endividamento e Solvência" in result

    def test_calculate_rentability_indicators_success(self, mock_mapper):
        """Test ROE and ROA calculations."""

        # Act & Assert: Calculate rentability indicators using the mock data.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper):

            # Act: Calculate rentability indicators using the mock data.
            result = calculate_rentability_indicators.invoke({"ticker": self.ticker})

            # Assert: Verify the calculated rentability indicators.
            assert "20.00%" in result  # ROE
            assert "10.00%" in result  # ROA
            assert "Rentabilidade (Evolução)" in result

    def test_calculate_growth_indicators_success(self, mock_mapper):
        """Test CAGR calculation for Revenue and Net Income."""

        # Act & Assert: Calculate growth indicators using the mock data.
        with (
            patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=self.mock_data),
            patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper),
        ):

            # Act: Calculate growth indicators using the mock data.
            result = calculate_growth_indicators.invoke({"ticker": self.ticker})

            # Assert: Verify the calculated CAGR values.
            assert "CAGR Receitas: 14.87%" in result
            assert "CAGR Lucros: 14.87%" in result

    def test_get_financial_evolution_success(self, mock_mapper):
        """Test quarterly evolution table generation."""

        # Act & Assert: Calculate quarterly evolution using the mock data.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper):

            # Act: Generate quarterly evolution table using the mock data.
            result = get_financial_evolution.invoke({"ticker": self.ticker})

            # Assert: Verify the generated financial evolution table.
            assert "Evolução Trimestral" in result

            # Check if values are present in the table
            assert "1,000" in result  # Revenue
            assert "200" in result  # Net Income
            assert "300" in result  # EBIT

    def test_get_auditor_info_success(self):
        """Test auditor info retrieval from 'parecer' dataframe."""

        # Act & Assert: Retrieve auditor info using the mock data.
        with patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=self.mock_data):

            # Act: Retrieve auditor info using the mock data.
            result = get_auditor_info.invoke({"ticker": self.ticker})

            # Assert: Verify the retrieved auditor information.
            assert "Auditor: Auditor Global Teste" in result
            assert "Opinião: Sem ressalvas" in result

    def test_get_auditor_info_fallback(self):
        """Test auditor info fallback to profile data when 'parecer' is missing."""

        # Arrange: Prepare empty consolidated data and mock profile data.
        empty_data = {}

        # Act & Assert: Retrieve auditor info using profile data as fallback.
        with (
            patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=empty_data),
            patch("nexus_equitygraph.tools.indicator_tools.get_company_profile_data", return_value=self.mock_profile),
        ):

            # Act: Retrieve auditor info using the mock profile data.
            result = get_auditor_info.invoke({"ticker": self.ticker})

            # Assert: Verify the retrieved auditor information from profile data.
            assert "Auditor: Auditor Global Teste (Cadastro CVM)" in result

    def test_calculate_wealth_distribution_success(self, mock_mapper):
        """Test DVA wealth distribution calculation."""

        # Act & Assert: Calculate wealth distribution using the mock data.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper):

            # Act: Calculate wealth distribution using the mock data.
            result = calculate_wealth_distribution.invoke({"ticker": self.ticker})

            # Assert: Verify the calculated wealth distribution percentages.
            assert "Pessoal (Salários): 16.7%" in result
            assert "Acionistas (Lucro): 66.7%" in result
            assert "Distribuição de Riqueza (DVA)" in result

    def test_tool_exception_handling(self):
        """Test if the decorator handles exceptions gracefully."""

        # Arrange: Simulate an error by making get_account_mapper raise an exception
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", side_effect=ValueError("Mock Error")):

            # Act: Define a simple tool function to test exception handling.
            # The decorator @handle_indicator_exceptions re-raises as IndicatorCalculationError
            # We need to import the exception to catch it, or check the string if it returns one (it raises).
            from nexus_equitygraph.core.exceptions import IndicatorCalculationError

            # Act & Assert: Verify that the decorator raises IndicatorCalculationError on exception.
            with pytest.raises(IndicatorCalculationError) as excinfo:
                calculate_valuation_indicators.invoke({"ticker": self.ticker, "current_price": 10.0})

            # Assert: Check if the exception message contains the expected text.
            assert "Erro no cálculo de valuation" in str(excinfo.value)

    def test_get_company_profile_error(self):
        """Test handling of company profile error."""

        # Act & Assert: Simulate an error in company profile retrieval.
        with patch(
            "nexus_equitygraph.tools.indicator_tools.get_company_profile_data", return_value={"error": "Not found"}
        ):

            # Act: Invoke the function to get the company profile.
            result = get_company_profile.invoke({"ticker": self.ticker})

            # Assert: Check if the returned profile contains the error message.
            assert "Not found" in result

    def test_calculate_valuation_indicators_no_shares(self):
        """Test valuation when share count is zero."""

        # Arrange: Create data with empty capital composition
        data_no_shares = self.mock_data.copy()
        data_no_shares["composicao_capital"] = pd.DataFrame()
        mapper_no_shares = CVMAccountMapper(data_no_shares)

        # Act & Assert: Calculate valuation indicators and check for warning about missing shares.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mapper_no_shares):

            # Act: Calculate valuation indicators.
            result = calculate_valuation_indicators.invoke({"ticker": self.ticker, "current_price": 10.0})
            # Assert: Check for warning message about missing share count.
            assert "AVISO: Número de ações não encontrado" in result

    def test_calculate_efficiency_indicators_insufficient_data(self, empty_mapper):
        """Test efficiency indicators with no comparison periods."""

        # Act & Assert: Calculate efficiency indicators and check for warning.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper):

            # Act: Calculate efficiency indicators.
            result = calculate_efficiency_indicators.invoke({"ticker": self.ticker})

            # Assert: Check for warning message about insufficient data.
            assert "Dados insuficientes" in result

    def test_calculate_debt_indicators_insufficient_data(self, empty_mapper):
        """Test debt indicators with no comparison periods."""

        # Act & Assert: Calculate debt indicators and check for warning.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper):

            # Act: Calculate debt indicators.
            result = calculate_debt_indicators.invoke({"ticker": self.ticker})

            # Assert: Check for warning message about insufficient data.
            assert "Dados insuficientes" in result

    def test_calculate_rentability_indicators_insufficient_data(self, empty_mapper):
        """Test rentability indicators with no comparison periods."""

        # Act & Assert: Calculate rentability indicators and check for warning.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper):

            # Act: Calculate rentability indicators.
            result = calculate_rentability_indicators.invoke({"ticker": self.ticker})

            # Assert: Check for warning message about insufficient data.
            assert "Dados insuficientes" in result

    def test_calculate_growth_indicators_no_dre(self):
        """Test growth indicators when DRE is missing."""

        # Act & Assert: Calculate growth indicators and check for warning.
        with patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value={}):

            # Act: Calculate growth indicators.
            result = calculate_growth_indicators.invoke({"ticker": self.ticker})

            # Assert: Check for warning message about missing DRE.
            assert "Dados DRE insuficientes" in result

    def test_calculate_growth_indicators_no_years(self):
        """Test growth indicators when DRE has no valid years."""

        # Arrange: Create data with empty DRE
        df_dre = pd.DataFrame({"DT_REFER": []})
        data = {"DRE": df_dre}

        # Act & Assert: Calculate growth indicators and check for warning.
        with patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=data):

            # Act: Calculate growth indicators.
            result = calculate_growth_indicators.invoke({"ticker": self.ticker})

            # Assert: Check for warning message about no valid years.
            assert "Sem dados de ano" in result

    def test_calculate_growth_indicators_single_year(self):
        """Test growth indicators with only one year of data."""

        # Arrange: Create data with single year of DRE,
        dt_2023 = datetime(2023, 12, 31)
        df_dre = pd.DataFrame(
            [
                {
                    "DT_REFER": dt_2023,
                    "CD_CONTA": "3.01",
                    "DS_CONTA": "Receita",
                    "VL_CONTA": 100.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                }
            ]
        )
        data = {"DRE": df_dre}

        # Act & Assert: Calculate growth indicators and check for warning.
        with patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=data):

            # Act: Calculate growth indicators.
            result = calculate_growth_indicators.invoke({"ticker": self.ticker})

            # Assert: Check for warning message about insufficient historical series.
            assert "Série histórica insuficiente" in result

    def test_calculate_growth_indicators_leap_year_exception(self):
        """Test leap year handling in growth indicators."""

        # Arrange: Create data with leap year and non-leap year dates
        dt_2024_leap = datetime(2024, 2, 29)
        dt_2019 = datetime(2019, 2, 28)

        df_dre = pd.DataFrame(
            [
                {
                    "DT_REFER": dt_2024_leap,
                    "CD_CONTA": "3.01",
                    "DS_CONTA": "Receita",
                    "VL_CONTA": 1000.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
                {
                    "DT_REFER": dt_2024_leap,
                    "CD_CONTA": "3.11",
                    "DS_CONTA": "Lucro",
                    "VL_CONTA": 200.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
                {
                    "DT_REFER": dt_2019,
                    "CD_CONTA": "3.01",
                    "DS_CONTA": "Receita",
                    "VL_CONTA": 500.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
                {
                    "DT_REFER": dt_2019,
                    "CD_CONTA": "3.11",
                    "DS_CONTA": "Lucro",
                    "VL_CONTA": 100.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
            ]
        )
        data = {"DRE": df_dre}
        mapper = CVMAccountMapper(data)

        # Act & Assert: Calculate growth indicators and check for exception.
        with (
            patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=data),
            patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mapper),
        ):

            # Act: Calculate growth indicators.
            result = calculate_growth_indicators.invoke({"ticker": self.ticker})

            # Assert: Check for exception message.
            assert "CAGR Receitas" in result

    def test_calculate_growth_indicators_profit_reversal(self):
        """Test profit reversal logic (Negative -> Positive)."""

        # Arrange: Create data with profit reversal scenario.
        dt_2023 = datetime(2023, 12, 31)
        dt_2018 = datetime(2018, 12, 31)

        df_dre = pd.DataFrame(
            [
                {
                    "DT_REFER": dt_2023,
                    "CD_CONTA": "3.11",
                    "DS_CONTA": "Lucro",
                    "VL_CONTA": 200.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
                {
                    "DT_REFER": dt_2018,
                    "CD_CONTA": "3.11",
                    "DS_CONTA": "Lucro",
                    "VL_CONTA": -100.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
                {
                    "DT_REFER": dt_2023,
                    "CD_CONTA": "3.01",
                    "DS_CONTA": "Receita",
                    "VL_CONTA": 1000.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
                {
                    "DT_REFER": dt_2018,
                    "CD_CONTA": "3.01",
                    "DS_CONTA": "Receita",
                    "VL_CONTA": 500.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
            ]
        )
        data = {"DRE": df_dre}
        mapper = CVMAccountMapper(data)

        # Act & Assert: Calculate growth indicators and check for profit reversal message.
        with (
            patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=data),
            patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mapper),
        ):

            # Act: Calculate growth indicators.
            result = calculate_growth_indicators.invoke({"ticker": self.ticker})

            # Assert: Check for profit reversal message.
            assert "Reversão de Prejuízo" in result

    def test_get_financial_evolution_no_dre(self, empty_mapper):
        """Test financial evolution when DRE is missing."""

        # Act & Assert: Calculate financial evolution and check for warning.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper):

            # Act: Calculate financial evolution.
            result = get_financial_evolution.invoke({"ticker": self.ticker})

            # Assert: Check for warning message about missing DRE.
            assert "Dados DRE não disponíveis" in result

    def test_calculate_wealth_distribution_zero_dva(self, empty_mapper):
        """Test wealth distribution when DVA is zero."""

        # Act & Assert: Calculate wealth distribution and check for zero DVA message.
        with patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper):

            # Act: Calculate wealth distribution.
            result = calculate_wealth_distribution.invoke({"ticker": self.ticker})

            # Assert: Check for zero DVA message.
            assert "DVA zerada ou indisponível" in result
