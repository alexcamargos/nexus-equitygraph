"""Tests for the helper functions in the tools module."""

import datetime

import pandas as pd
import pytest

from nexus_equitygraph.tools import helpers


@pytest.fixture(autouse=True)
def clear_helpers_caches():
    """Clear lru_cache for helper functions before each test."""

    helpers.get_account_mapper.cache_clear()
    helpers.get_cvm_client.cache_clear()
    helpers.get_consolidated_data.cache_clear()


class TestFactoryFunctions:
    """Tests for factory and singleton functions."""

    def test_get_cvm_client_returns_singleton(self, mocker):
        """Should return the same CVMClient instance (cached singleton)."""

        # Act: Get client multiple times.
        client1 = helpers.get_cvm_client()
        client2 = helpers.get_cvm_client()

        # Assert: Verify it's effectively a singleton (or cached).
        assert client1 is client2
        assert isinstance(client1, helpers.CVMClient)

    def test_get_consolidated_data_calls_client(self, mocker):
        """Should call CVMClient to fetch consolidated data and return it."""

        # Arrange: Mock CVMClient and its return value.
        mock_client = mocker.Mock()
        mocker.patch("nexus_equitygraph.tools.helpers.get_cvm_client", return_value=mock_client)
        expected_data = {"DRE": pd.DataFrame({"test": [1]})}
        mock_client.get_consolidated_company_data.return_value = expected_data

        # Act: Execute.
        result = helpers.get_consolidated_data("PETR3")

        # Assert: Verify client was called and data returned correctly.
        mock_client.get_consolidated_company_data.assert_called_with("PETR3")
        assert "DRE" in result
        pd.testing.assert_frame_equal(result["DRE"], expected_data["DRE"])

    def test_get_account_mapper_caching(self, mocker):
        """Should cache CVMAccountMapper instances by ticker."""

        # Arrange: Mock return value of data fetch.
        mocker.patch("nexus_equitygraph.tools.helpers.get_consolidated_data", return_value={})

        # Act: Execute for the same ticker twice.
        mapper1 = helpers.get_account_mapper("VALE3")
        mapper2 = helpers.get_account_mapper("VALE3")

        # Assert: Verify it's the same object (cached).
        assert mapper1 is mapper2


class TestGetRowValue:
    """Tests for _get_row_value internal function."""

    def test_returns_value_if_exists(self):
        """Should return the value from the row if the key exists."""

        # Arrange: Setup a series with an existing name key.
        row = pd.Series({"name": "Test Company", "value": 100})
        key = "name"

        # Act: Execute the function to extract the row value.
        result = helpers._get_row_value(row, key)

        # Assert: Verify that the correct company name is returned.
        assert result == "Test Company"

    def test_returns_default_if_missing(self):
        """Should return the default value if the key is missing from the row."""

        # Arrange: Setup a series with a missing value key and specify a default fallback.
        row = pd.Series({"name": "Test Company"})
        key = "value"

        # Act: Execute the function with a custom default value.
        result = helpers._get_row_value(row, key, not_found_value="N/A")

        # Assert: Verify that the specified default value is returned when the key is missing.
        assert result == "N/A"

    def test_returns_default_if_nan(self):
        """Should return the default value if the value in the row is NaN."""

        # Arrange: Setup a series where the key has a NaN value and specify a fallback.
        row = pd.Series({"name": float("nan")})
        key = "name"

        # Act: Execute the function to handle the NaN value.
        result = helpers._get_row_value(row, key, not_found_value="Missing")

        # Assert: Verify that the specified default value is returned for NaN.
        assert result == "Missing"


class TestBuildMetadata:
    """Tests for build_metadata function."""

    def test_formats_metadata_correctly(self):
        """Should generate a correctly formatted metadata string with sources and dates."""

        # Arrange: Setup sources and periods (date and string).
        sources = ["Source A", "Source B"]
        periods = [datetime.date(2023, 1, 1), "2024"]

        # Act: Execute the function to build the metadata string.
        result = helpers.build_metadata(sources, periods)

        # Assert: Verify that sources, dates, and headers are correctly formatted in the metadata.
        assert "Source A, Source B" in result
        assert "01/01/2023" in result
        assert "2024" in result
        assert "> **Metadados:**" in result


class TestGetCompanyProfileData:
    """Tests for get_company_profile_data function."""

    def test_returns_error_if_cvm_code_not_found(self, mocker):
        """Should return error message if ticker cannot be resolved to a CVM code."""

        # Arrange: Mock client to return None code.
        mock_client = mocker.Mock()
        mocker.patch("nexus_equitygraph.tools.helpers.get_cvm_client", return_value=mock_client)
        mock_client.get_cvm_code_by_name.return_value = None

        # Act: Execute.
        result = helpers.get_company_profile_data("INVALID")

        # Assert: Error returned.
        assert "error" in result
        assert "não encontrada" in result["error"].lower()

    def test_returns_error_if_not_found_in_cadastral(self, mocker):
        """Should return error message if CVM code is valid but missing from cadastral dataset."""

        # Arrange: Mock client code found but missing in cadastral.
        mock_client = mocker.Mock()
        mocker.patch("nexus_equitygraph.tools.helpers.get_cvm_client", return_value=mock_client)
        mock_client.get_cvm_code_by_name.return_value = 12345
        mock_client.get_cadastral_info.return_value = pd.DataFrame({"CD_CVM": ["99999"]})

        # Act: Execute.
        result = helpers.get_company_profile_data("TICKER")

        # Assert: Specific error message substring found.
        assert "error" in result
        assert "não encontrado no processamento cadastral" in result["error"].lower()

    def test_returns_profile_successfully(self, mocker):
        """Should return a full company profile dictionary when data is correctly found."""

        # Arrange: Mock valid cadastral info.
        mock_client = mocker.Mock()
        mocker.patch("nexus_equitygraph.tools.helpers.get_cvm_client", return_value=mock_client)
        mock_client.get_cvm_code_by_name.return_value = 123
        cad_df = pd.DataFrame(
            {
                "CD_CVM": ["000123"],
                "DENOM_SOCIAL": ["Petro S.A."],
                "DENOM_COMERC": ["Petro"],
                "CNPJ_CIA": ["123"],
                "SETOR_ATIV": ["Oil"],
                "DT_REG": ["2000-01-01"],
                "DT_CONST": ["1950-01-01"],
                "MUN": ["Rio"],
                "UF": ["RJ"],
                "SIT": ["Ativa"],
                "AUDITOR": ["PwC"],
            }
        )
        mock_client.get_cadastral_info.return_value = cad_df

        # Act: Execute.
        result = helpers.get_company_profile_data("PETR4")

        # Assert: All fields present and correctly mapped.
        assert result["company_name"] == "Petro S.A."
        assert result["auditor"] == "PwC"


class TestFormatPercentageCurrency:
    """Tests for format_percentage_currency function."""

    def test_formats_correctly(self):
        """Should format the distribution line with correct percentage and currency symbols."""

        # Arrange: Setup label, base value, and total for percentage calculation.
        label = "Salários"
        value = 1000.0
        total = 5000.0

        # Act: Execute the function to format the distribution line.
        result = helpers.format_percentage_currency(label, value, total)

        # Assert: Verify that the percentage and currency are correctly formatted (20.0%).
        assert result == "Salários: 20.0% (R$ 1,000)"

    def test_handles_zero_total(self):
        """Should handle cases where total is zero by returning 0.0% to avoid division by zero."""

        # Arrange: Call function with a zero total to test division safety.
        result = helpers.format_percentage_currency("Test", 100.0, 0.0)

        # Assert: Verify that it returns 0.0% instead of crashing with division by zero.
        assert "0.0%" in result


class TestEnsureSASuffix:
    """Tests for ensure_sa_suffix function."""

    @pytest.mark.parametrize(
        "ticker, expected",
        [
            ("petr4", "PETR4.SA"),
            ("VALE3.SA", "VALE3.SA"),
            ("itub4  ", "ITUB4.SA"),
            ("AAPL", "AAPL.SA"),
            ("VERYLONGTICKER", "VERYLONGTICKER"),  # Should not add if > 6 chars
        ],
    )
    def test_adds_suffix_scenarios(self, ticker, expected):
        """Should add .SA suffix to tickers when appropriate and normalize them to uppercase."""

        # Act: Execute the function to ensure the .SA suffix is correctly added/normalized.
        result = helpers.ensure_sa_suffix(ticker)

        # Assert: Verify that the ticker matches the expected suffix and normalization.
        assert result == expected


class TestMarketIndicators:
    """Tests for market indicator calculation helpers."""

    @pytest.fixture
    def price_history(self):
        """Provide a sample price history DataFrame for indicator tests."""

        data = {"Close": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0]}
        return pd.DataFrame(data)

    def test_calculate_sma_status_above(self, price_history):
        """Should return a status message indicating the price is ABOVE the SMA."""

        # Arrange: Calculate the 5-day SMA from history where the current price is above the average.
        result = helpers.calculate_sma_status(price_history.head(5), 15.0, 5)

        # Assert: Verify that the status correctly indicates the price is 'acima' (above).
        assert "acima" in result
        assert "12.00" in result

    def test_calculate_sma_status_below(self, price_history):
        """Should return a status message indicating the price is BELOW the SMA."""

        # Arrange: Calculate the 5-day SMA where the current price is below the average.
        result = helpers.calculate_sma_status(price_history.head(5), 10.0, 5)

        # Assert: Verify that the status correctly indicates the price is 'abaixo' (below).
        assert "abaixo" in result

    def test_calculate_sma_insufficient_data(self, price_history):
        """Should return an 'insufficient data' message when history length is less than window."""

        # Arrange: Test SMA calculation with a window larger than the available history.
        result = helpers.calculate_sma_status(price_history, 15.0, 20)

        # Assert: Verify that it returns the 'insufficient data' error message.
        assert "Dados insuficientes" in result

    def test_calculate_rsi_normal(self, price_history):
        """Should calculate the RSI correctly for a given window."""

        # Arrange: Execute RSI calculation for a 5-day window on increasing prices.
        result = helpers.calculate_rsi(price_history, 5)

        # Assert: Verify that the RSI is correctly calculated (expected 100.00 for strictly increasing data).
        assert "RSI 5" in result
        assert "100.00" in result

    def test_calculate_rsi_insufficient_data(self):
        """Should return 'insufficient data' for RSI when history is too short."""

        # Arrange: Window 14 on 5 rows.
        df = pd.DataFrame({"Close": [1, 2, 3, 4, 5]})
        result = helpers.calculate_rsi(df, 14)

        # Assert: Verify insufficient data message.
        assert "Dados insuficientes" in result

    def test_calculate_rsi_normal_ratio(self):
        """Should calculate a realistic RSI value when both gains and losses occur."""

        # Arrange: Mix of gains and losses.
        df = pd.DataFrame({"Close": [10, 12, 11, 13, 12, 14, 13, 15, 14, 16]})

        # Act: Calculate RSI with a small window.
        result = helpers.calculate_rsi(df, 3)

        # Assert: Verify RSI is calculated and not stuck at 100.
        assert "RSI 3" in result
        assert "100.00" not in result

    def test_calculate_volatility(self, price_history):
        """Should calculate volatility based on the standard deviation of returns."""

        # Act: Execute volatility calculation on the price history.
        result = helpers.calculate_volatility(price_history)

        # Assert: Verify that the volatility message is returned.
        assert "Volatilidade" in result

    def test_calculate_volatility_insufficient_data(self):
        """Should return 'insufficient data' for volatility when history has less than 2 points."""

        # Arrange: Only 1 row.
        df = pd.DataFrame({"Close": [10]})

        # Act: Calculate volatility.
        result = helpers.calculate_volatility(df)

        # Assert: Verify insufficient data message.
        assert "Dados insuficientes" in result

    def test_calculate_price_range(self, price_history):
        """Should return the maximum and minimum prices found in the price history."""

        # Act: Execute price range calculation to find high and low prices.
        result = helpers.calculate_price_range(price_history)

        # Assert: Verify that both max and min prices are present in the output.
        assert "19.00" in result
        assert "10.00" in result

    def test_calculate_price_range_empty(self):
        """Should return 'insufficient data' for price range when DataFrame is empty."""

        # Arrange: Empty df.
        df = pd.DataFrame(columns=["Close"])

        # Act: Calculate price range.
        result = helpers.calculate_price_range(df)

        # Assert: Verify insufficient data message.
        assert "Dados insuficientes" in result

    def test_determine_trend_alta(self, price_history):
        """Should identify an 'alta' (uptrend) trend when prices are strictly increasing."""

        # Act: Determine the 5-day trend for strictly increasing prices.
        result = helpers.determine_trend(price_history, 5)

        # Assert: Verify that the trend is correctly identified as 'alta' (up).
        assert "alta" in result

    def test_determine_trend_baixa(self):
        """Should identify a 'baixa' (downtrend) trend when prices are strictly decreasing."""

        # Arrange: Create a DataFrame with strictly decreasing prices.
        df = pd.DataFrame({"Close": [20, 19, 18, 17, 16]})

        # Act: Determine the 5-day trend.
        result = helpers.determine_trend(df, 5)

        # Assert: Verify that the trend is correctly identified as 'baixa' (down).
        assert "baixa" in result

    def test_determine_trend_insufficient_data(self):
        """Should return 'insufficient data' for trend when history is shorter than the requested days."""

        # Arrange: Less than 'days'.
        df = pd.DataFrame({"Close": [10, 11]})

        # Act: Determine trend for 5 days.
        result = helpers.determine_trend(df, 5)

        # Assert: Verify insufficient data message.
        assert "Dados insuficientes" in result

    def test_determine_trend_lateral(self):
        """Should identify a 'lateral' trend when prices are not monotonically increasing or decreasing."""

        # Arrange: Fluctuating prices (not monotonic).
        df = pd.DataFrame({"Close": [10, 12, 11, 13, 12]})

        # Act: Determine trend.
        result = helpers.determine_trend(df, 5)

        # Assert: Verify trend is identified as 'lateral'.
        assert "lateral" in result

    def test_determine_general_trend(self, price_history):
        """Should identify the general trend by comparing the start and end prices of the period."""

        # Act: Execute general trend determination (comparing period start to end).
        result = helpers.determine_general_trend(price_history)

        # Assert: Verify that the general trend is identified as 'alta'.
        assert "alta" in result

    def test_determine_general_trend_insufficient_data(self):
        """Should return 'insufficient data' for general trend when history has less than 2 points."""

        # Arrange: 1 row.
        df = pd.DataFrame({"Close": [10]})

        # Act: Determine general trend.
        result = helpers.determine_general_trend(df)

        # Assert: Verify insufficient data message.
        assert "Dados insuficientes" in result

    def test_determine_general_trend_baixa(self):
        """Should identify a general 'baixa' trend when the end price is lower than the start price."""

        # Arrange: Start 20, End 10.
        df = pd.DataFrame({"Close": [20, 15, 10]})

        # Act: Determine general trend.
        result = helpers.determine_general_trend(df)

        # Assert: Verify trend is 'baixa'.
        assert "baixa" in result

    def test_determine_general_trend_lateral(self):
        """Should identify a general 'lateral' trend when start and end prices are equal."""

        # Arrange: Start 10, End 10.
        df = pd.DataFrame({"Close": [10, 15, 10]})

        # Act: Determine general trend.
        result = helpers.determine_general_trend(df)

        # Assert: Verify trend is 'lateral'.
        assert "lateral" in result


class TestProcessAndFormatDRE:
    """Tests for process_and_format_dre_for_year function."""

    def test_returns_empty_if_no_data_for_year(self):
        """Should return an empty list if there is no DRE data for the specified year."""

        # Arrange: Create an empty DataFrame with reference date column.
        df = pd.DataFrame(columns=["DT_REFER"])

        # Act: Execute DRE formatting with no records available.
        result = helpers.process_and_format_dre_for_year(df, "2023")

        # Assert: Verify that an empty list is returned.
        assert result == []

    def test_formats_dre_data_correctly(self):
        """Should format the DRE summary correctly when valid data is present."""

        # Arrange: Setup mock DRE data with specific accounts and values for 2023.
        data = {
            "DT_REFER": ["2023-12-31", "2023-12-31", "2023-12-31"],
            "CD_CONTA": ["3.01", "3.11", "3.99"],
            "DS_CONTA": ["Receita", "EBIT", "Lucro"],
            "VL_CONTA": [1000, 500, 200],
            "ORDEM_EXERC": ["ÚLTIMO", "ÚLTIMO", "ÚLTIMO"],
        }
        df = pd.DataFrame(data)

        # Act: Execute DRE formatting for the year 2023.
        result = helpers.process_and_format_dre_for_year(df, "2023")

        # Assert: Verify that the summary header and specific account data are present.
        assert any("DRE Resumo" in line for line in result)
        assert any("Receita" in line for line in result)
        assert any("1000" in line for line in result)

    def test_formats_dre_data_using_conftest_fixture(self, mock_cvm_data):
        """Should correctly format DRE data using the global mock_cvm_data fixture."""

        # Arrange: Use DRE data from conftest.
        df_dre = mock_cvm_data["DRE"]

        # Act: Execute for 2023.
        result = helpers.process_and_format_dre_for_year(df_dre, "2023")

        # Assert: Verify conftest values (1000.0 exists in conftest for 3.01 in 2023).
        assert any("DRE Resumo" in line for line in result)
        assert any("1000" in line for line in result)

    def test_formats_dre_data_with_accumulated_logic(self):
        """Should correctly handle period prioritization (YTD vs Quarter) in DRE results."""

        # Arrange: Setup mock DRE data with duplicates and start dates.
        data = {
            "DT_REFER": ["2023-12-31", "2023-12-31"],
            "DT_INI_EXERC": ["2023-01-01", "2023-07-01"],  # Jan is 'earlier' -> keep first
            "CD_CONTA": ["3.01", "3.01"],
            "DS_CONTA": ["Receita", "Receita Trim."],
            "VL_CONTA": [1000, 300],
            "ORDEM_EXERC": ["ÚLTIMO", "ÚLTIMO"],
        }
        df = pd.DataFrame(data)

        # Act: Execute.
        result = helpers.process_and_format_dre_for_year(df, "2023")

        # Assert: Should keep the 1000 value (Accumulated).
        assert any("1000" in line for line in result)
        assert not any("300" in line for line in result)


class TestProcessAndFormatBPP:
    """Tests for process_and_format_bpp_for_year function."""

    def test_returns_empty_if_no_bpp_data(self, mocker):
        """Should return an empty list if no BPP data is found in the mapper."""

        # Arrange: Setup a mock mapper that contains no BPP (Balance Sheet) data.
        mapper = mocker.Mock()
        mapper.data = {}

        # Act: Execute BPP formatting.
        result = helpers.process_and_format_bpp_for_year(mapper, "2023")

        # Assert: Verify that an empty list is returned when data is missing.
        assert result == []

    def test_formats_bpp_equity_correctly(self, mocker):
        """Should correctly extract and format Equity data from the BPP records."""

        # Arrange: Setup a mock mapper with valid BPP data and equity return value.
        mapper = mocker.Mock()
        mapper.data = {"BPP": pd.DataFrame({"DT_REFER": ["2023-12-31"]})}
        mapper.get_equity.return_value = "R$ 5,000,000"

        # Act: Execute BPP formatting for the year 2023.
        result = helpers.process_and_format_bpp_for_year(mapper, "2023")

        # Assert: Verify that the Equity (Patrimônio Líquido) is correctly extracted and formatted.
        assert any("Patrimônio Líquido: R$ 5,000,000" in line for line in result)

    def test_formats_bpp_using_conftest_fixture(self, mocker, mock_cvm_data):
        """Should correctly extract Equity using data provided by the mock_cvm_data fixture."""

        # Arrange: Mock mapper that behaves like a real one with conftest data.
        mapper = mocker.Mock()
        mapper.data = mock_cvm_data
        mapper.get_equity.return_value = "R$ 1.000"  # Value in conftest for 2023

        # Act: Execute.
        result = helpers.process_and_format_bpp_for_year(mapper, "2023")

        # Assert: Verify match with conftest-derived value.
        assert any("Patrimônio Líquido: R$ 1.000" in line for line in result)

    def test_returns_empty_if_bpp_year_empty(self, mocker):
        """Should return an empty list if there is no BPP data for the requested year."""

        # Arrange: Mapper has BPP data but not for 2024.
        mapper = mocker.Mock()
        mapper.data = {"BPP": pd.DataFrame({"DT_REFER": ["2023-12-31"]})}

        # Act: Execute for 2024.
        result = helpers.process_and_format_bpp_for_year(mapper, "2024")

        # Assert: Empty.
        assert result == []
