"""Tests for the financial indicator tools using global mocks."""

from datetime import datetime

import pandas as pd
import pytest
import requests

from nexus_equitygraph.core.exceptions import CVMDataError, IndicatorCalculationError, handle_indicator_exceptions
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

    def test_get_company_profile_success(self, mocker):
        """Test retrieving company profile with valid data."""

        # Arrange: Mock the data retrieval function to return the mock profile.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_company_profile_data", return_value=self.mock_profile)

        # Act: Invoke the function to get the company profile.
        result = get_company_profile.invoke({"ticker": self.ticker})

        # Assert: Check if the returned profile contains expected information.
        assert "Nexus Tech S.A." in result
        assert "12.345.678/0001-90" in result
        assert "Metadados" in result

    def test_calculate_valuation_indicators_success(self, mocker, mock_mapper):
        """Test valuation calculations (P/E, EV/EBITDA, etc.)."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper)

        # Act: Calculate valuation indicators using the mock data.
        result = calculate_valuation_indicators.invoke({"ticker": self.ticker, "current_price": 10.0})

        # Assert: Verify the calculated valuation indicators.
        assert "Market Cap: R$ 10.000,00" in result
        assert "P/L: 50.00" in result
        assert "P/VP: 10.00" in result
        assert "EV/EBITDA: 31.56" in result

    def test_calculate_valuation_indicators_edge_cases(self, mocker):
        """Test valuation with zero/negative values to ensure no division errors."""

        # Setup: Create a mock mapper with zero/negative values.
        mock_mapper = mocker.MagicMock()
        mock_mapper.share_count = 1_000
        mock_mapper.get_equity.return_value = 10_000
        mock_mapper.get_net_income.return_value = 0  # Zero earnings -> No P/L
        mock_mapper.get_ebitda.return_value = -500  # Negative EBITDA -> No EV/EBITDA
        mock_mapper.get_gross_debt.return_value = 2_000
        mock_mapper.get_cash_and_equivalents.return_value = 500
        mock_mapper.get_dividends_paid.return_value = 0
        mock_mapper.get_operating_cash_flow.return_value = 100
        mock_mapper.get_capex.return_value = -50

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper)

        # Act: Calculate valuation indicators using the mock data.
        result = calculate_valuation_indicators.invoke({"ticker": self.ticker, "current_price": 10.0})

        assert "Market Cap" in result
        # Should be skipped due to zero/negative values logic
        assert "P/L" not in result
        assert "EV/EBITDA" not in result
        # Should be present
        assert "P/VP" in result

    def test_calculate_efficiency_indicators_success(self, mocker, mock_mapper):
        """Test efficiency margins (Gross, EBIT, Net)."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper)

        # Act: Calculate efficiency indicators using the mock data.
        result = calculate_efficiency_indicators.invoke({"ticker": self.ticker})

        # Assert: Verify the calculated efficiency margins.
        assert "50.00%" in result  # Gross Margin
        assert "30.00%" in result  # EBIT Margin
        assert "20.00%" in result  # Net Margin
        assert "Eficiência (Margens)" in result

    def test_calculate_debt_indicators_success(self, mocker, mock_mapper):
        """Test debt and liquidity indicators."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper)

        # Act: Calculate debt indicators using the mock data.
        result = calculate_debt_indicators.invoke({"ticker": self.ticker})

        # Assert: Verify the calculated debt and liquidity indicators.
        assert "0.31x" in result
        assert "2.00" in result
        assert "Endividamento e Solvência" in result

    def test_calculate_rentability_indicators_success(self, mocker, mock_mapper):
        """Test ROE and ROA calculations."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper)

        # Act: Calculate rentability indicators using the mock data.
        result = calculate_rentability_indicators.invoke({"ticker": self.ticker})

        # Assert: Verify the calculated rentability indicators.
        assert "20.00%" in result  # ROE
        assert "10.00%" in result  # ROA
        assert "Rentabilidade (Evolução)" in result

    def test_calculate_growth_indicators_success(self, mocker, mock_mapper):
        """Test CAGR calculation for Revenue and Net Income."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=self.mock_data)
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper)

        # Act: Calculate growth indicators using the mock data.
        result = calculate_growth_indicators.invoke({"ticker": self.ticker})

        # Assert: Verify the calculated CAGR values.
        assert "CAGR Receitas: 14.87%" in result
        assert "CAGR Lucros: 14.87%" in result

    def test_get_financial_evolution_success(self, mocker, mock_mapper):
        """Test quarterly evolution table generation."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper)

        # Act: Generate quarterly evolution table using the mock data.
        result = get_financial_evolution.invoke({"ticker": self.ticker})

        # Assert: Verify the generated financial evolution table.
        assert "Evolução Trimestral" in result

        # Check if values are present in the table
        assert "1,000" in result  # Revenue
        assert "200" in result  # Net Income
        assert "300" in result  # EBIT

    def test_get_auditor_info_success(self, mocker):
        """Test auditor info retrieval from 'parecer' dataframe."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=self.mock_data)

        # Act: Retrieve auditor info using the mock data.
        result = get_auditor_info.invoke({"ticker": self.ticker})

        # Assert: Verify the retrieved auditor information.
        assert "Auditor: Auditor Global Teste" in result
        assert "Opinião: Sem ressalvas" in result

    def test_get_auditor_info_fallback(self, mocker):
        """Test auditor info fallback to profile data when 'parecer' is missing."""

        # Setup: Prepare empty consolidated data and mock profile data.
        empty_data = {}

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=empty_data)
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_company_profile_data", return_value=self.mock_profile)

        # Act: Retrieve auditor info using the mock profile data.
        result = get_auditor_info.invoke({"ticker": self.ticker})

        # Assert: Verify the retrieved auditor information from profile data.
        assert "Auditor: Auditor Global Teste (Cadastro CVM)" in result

    def test_calculate_wealth_distribution_success(self, mocker, mock_mapper):
        """Test DVA wealth distribution calculation."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mock_mapper)

        # Act: Calculate wealth distribution using the mock data.
        result = calculate_wealth_distribution.invoke({"ticker": self.ticker})

        # Assert: Verify the calculated wealth distribution percentages.
        assert "Pessoal (Salários): 16.7%" in result
        assert "Acionistas (Lucro): 66.7%" in result
        assert "Distribuição de Riqueza (DVA)" in result

    def test_tool_exception_handling(self, mocker):
        """Test if the decorator handles exceptions gracefully."""

        # Arrange: Setup mocks to raise an exception during data retrieval.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", side_effect=ValueError("Mock Error"))

        # Act & Assert: Verify that the decorator raises IndicatorCalculationError on exception.
        with pytest.raises(IndicatorCalculationError) as excinfo:
            calculate_valuation_indicators.invoke({"ticker": self.ticker, "current_price": 10.0})

        # Assert: Check if the exception message contains the expected text.
        assert "Erro no cálculo de valuation" in str(excinfo.value)

    def test_decorator_handle_indicator_exceptions_isolation(self):
        """Test the exception handler decorator in isolation for different error types."""

        # 1. Test Calculation Error (ValueError -> IndicatorCalculationError)
        @handle_indicator_exceptions("test_calc")
        def fail_calc(ticker):
            raise ValueError("Math error")

        # Act & Assert: Verify that IndicatorCalculationError is raised.
        with pytest.raises(IndicatorCalculationError) as exc:
            fail_calc("TEST3")
        assert "Erro no cálculo de test_calc" in str(exc.value)

        # 2. Test Network Error (RequestException -> CVMDataError)
        @handle_indicator_exceptions("test_net")
        def fail_net(ticker):
            raise requests.RequestException("Connection lost")

        # Act & Assert: Verify that CVMDataError is raised.
        with pytest.raises(CVMDataError) as exc:
            fail_net("TEST3")
        assert "Erro de rede" in str(exc.value)

        # 3. Test Unexpected Error (Generic Exception -> Returns String for Agent)
        @handle_indicator_exceptions("test_bug")
        def fail_bug(ticker):
            raise Exception("Unexpected bug")

        # Act: Call the function and capture the result.
        result = fail_bug("TEST3")
        assert "Erro test_bug: Unexpected bug" in result

    def test_get_company_profile_error(self, mocker):
        """Test handling of company profile error."""

        # Arrange: Mock the data retrieval function to return an error.
        mocker.patch(
            "nexus_equitygraph.tools.indicator_tools.get_company_profile_data", return_value={"error": "Not found"}
        )

        # Act: Invoke the function to get the company profile.
        result = get_company_profile.invoke({"ticker": self.ticker})

        # Assert: Check if the returned profile contains the error message.
        assert "Not found" in result

    def test_calculate_valuation_indicators_no_shares(self, mocker):
        """Test valuation when share count is zero."""

        # Setup: Create data with no share count information.
        data_no_shares = self.mock_data.copy()
        data_no_shares["composicao_capital"] = pd.DataFrame()
        mapper_no_shares = CVMAccountMapper(data_no_shares)

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mapper_no_shares)

        # Act: Calculate valuation indicators.
        result = calculate_valuation_indicators.invoke({"ticker": self.ticker, "current_price": 10.0})
        # Assert: Check for warning message about missing share count.
        assert "AVISO: Número de ações não encontrado" in result

    def test_calculate_efficiency_indicators_insufficient_data(self, mocker, empty_mapper):
        """Test efficiency indicators with no comparison periods."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper)

        # Act: Calculate efficiency indicators.
        result = calculate_efficiency_indicators.invoke({"ticker": self.ticker})

        # Assert: Check for warning message about insufficient data.
        assert "Dados insuficientes" in result

    def test_calculate_debt_indicators_insufficient_data(self, mocker, empty_mapper):
        """Test debt indicators with no comparison periods."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper)

        # Act: Calculate debt indicators.
        result = calculate_debt_indicators.invoke({"ticker": self.ticker})

        # Assert: Check for warning message about insufficient data.
        assert "Dados insuficientes" in result

    def test_calculate_rentability_indicators_insufficient_data(self, mocker, empty_mapper):
        """Test rentability indicators with no comparison periods."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper)

        # Act: Calculate rentability indicators.
        result = calculate_rentability_indicators.invoke({"ticker": self.ticker})

        # Assert: Check for warning message about insufficient data.
        assert "Dados insuficientes" in result

    def test_calculate_growth_indicators_no_dre(self, mocker):
        """Test growth indicators when DRE is missing."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value={})

        # Act: Calculate growth indicators.
        result = calculate_growth_indicators.invoke({"ticker": self.ticker})

        # Assert: Check for warning message about missing DRE.
        assert "Dados DRE insuficientes" in result

    def test_calculate_growth_indicators_no_years(self, mocker):
        """Test growth indicators when DRE has no valid years."""

        # Arrange: Create data with empty DRE, no years available.
        df_dre = pd.DataFrame({"DT_REFER": []})
        data = {"DRE": df_dre}

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=data)

        # Act: Calculate growth indicators.
        result = calculate_growth_indicators.invoke({"ticker": self.ticker})

        # Assert: Check for warning message about no valid years.
        assert "Sem dados de ano" in result

    def test_calculate_growth_indicators_single_year(self, mocker):
        """Test growth indicators with only one year of data."""

        # Setup: Create data with single year of DRE, which is insufficient for growth calculation.
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

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=data)

        # Act: Calculate growth indicators.
        result = calculate_growth_indicators.invoke({"ticker": self.ticker})

        # Assert: Check for warning message about insufficient historical series.
        assert "Série histórica insuficiente" in result

    def test_calculate_growth_indicators_leap_year_exception(self, mocker):
        """Test leap year handling in growth indicators."""

        # Setup: Create data with leap year dates.
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

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=data)
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mapper)

        # Act: Calculate growth indicators.
        result = calculate_growth_indicators.invoke({"ticker": self.ticker})

        # Assert: Check for exception message.
        assert "CAGR Receitas" in result

    def test_calculate_growth_indicators_profit_reversal(self, mocker):
        """Test profit reversal logic (Negative -> Positive)."""

        # Setup: Create data with profit reversal.
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

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_consolidated_data", return_value=data)
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=mapper)

        # Act: Calculate growth indicators.
        result = calculate_growth_indicators.invoke({"ticker": self.ticker})

        # Assert: Check for profit reversal message.
        assert "Reversão de Prejuízo" in result

    def test_get_financial_evolution_no_dre(self, mocker, empty_mapper):
        """Test financial evolution when DRE is missing."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper)

        # Act: Calculate financial evolution.
        result = get_financial_evolution.invoke({"ticker": self.ticker})

        # Assert: Check for warning message about missing DRE.
        assert "Dados DRE não disponíveis" in result

    def test_calculate_wealth_distribution_zero_dva(self, mocker, empty_mapper):
        """Test wealth distribution when DVA is zero."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch("nexus_equitygraph.tools.indicator_tools.get_account_mapper", return_value=empty_mapper)

        # Act: Calculate wealth distribution.
        result = calculate_wealth_distribution.invoke({"ticker": self.ticker})

        # Assert: Check for zero DVA message.
        assert "DVA zerada ou indisponível" in result
