"""Tests for the market tools module."""

import pytest

from nexus_equitygraph.tools import market_tools


@pytest.fixture
def yf_ticker_mock(mocker):
    """Provide a patched `yf.Ticker` instance for tests.

    Returns the mocked ticker instance so tests can set `.info` and
    `.history` as needed.
    """

    patched = mocker.patch("nexus_equitygraph.tools.market_tools.yf.Ticker")
    instance = mocker.Mock()
    patched.return_value = instance

    return instance


class TestGetCurrentStockPrice:
    """Tests for get_current_stock_price function."""

    @pytest.mark.parametrize(
        "mock_info, history_price, expected_price",
        [
            ({"currentPrice": 42.5}, None, 42.5),  # Normal case: Price from info
            ({}, 33.7, 33.7),  # Fallback case: Price from history
            ({}, None, 0.0),  # Edge case: No data found
        ],
    )
    def test_get_current_price_scenarios(self, mocker, yf_ticker_mock, mock_info, history_price, expected_price):
        """Should return price from info, history fallback, or zero."""

        # Arrange: Setup mock info and historical data.
        yf_ticker_mock.info = mock_info

        historical_data = mocker.MagicMock()
        if history_price is not None:
            historical_data.empty = False
            historical_data.__getitem__.return_value.iloc.__getitem__.return_value = history_price
        else:
            historical_data.empty = True
        yf_ticker_mock.history.return_value = historical_data

        # Act: Execute the function to get the current price.
        result = market_tools.get_current_stock_price.invoke({"ticker": "PETR4"})

        # Assert: Verify that the returned price matches our expectation for this scenario.
        assert result == expected_price


class TestGetStockPriceHistory:
    """Tests for get_stock_price_history function."""

    def test_returns_formatted_history(self, mocker, yf_ticker_mock):
        """Should return formatted history with indicators if data is available."""

        # Arrange: Mock all technical indicators and price history data.
        mock_sma = mocker.patch("nexus_equitygraph.tools.market_tools.calculate_sma_status")
        mock_rsi = mocker.patch("nexus_equitygraph.tools.market_tools.calculate_rsi")
        mock_volatility = mocker.patch("nexus_equitygraph.tools.market_tools.calculate_volatility")
        mock_price_range = mocker.patch("nexus_equitygraph.tools.market_tools.calculate_price_range")
        mock_trend = mocker.patch("nexus_equitygraph.tools.market_tools.determine_trend")
        mock_general_trend = mocker.patch("nexus_equitygraph.tools.market_tools.determine_general_trend")
        mock_metadata = mocker.patch("nexus_equitygraph.tools.market_tools.build_metadata")

        historical_data = mocker.MagicMock()
        historical_data.empty = False
        historical_data.__getitem__.return_value.iloc.__getitem__.return_value = 100.0
        yf_ticker_mock.history.return_value = historical_data

        mock_sma.side_effect = ["SMA50", "SMA200"]
        mock_rsi.return_value = "RSI"
        mock_volatility.return_value = "Volatility"
        mock_price_range.return_value = "PriceRange"
        mock_trend.return_value = "Trend"
        mock_general_trend.return_value = "GeneralTrend"
        mock_metadata.return_value = "\nFooter"

        # Act: Execute the function to get formatted stock history.
        result = market_tools.get_stock_price_history.invoke({"ticker": "PETR4", "period": "1y"})

        # Assert: Ensure all calculated indicators and metadata are present in the output.
        assert "SMA50" in result
        assert "SMA200" in result
        assert "RSI" in result
        assert "Volatility" in result
        assert "PriceRange" in result
        assert "Trend" in result
        assert "GeneralTrend" in result
        assert "Footer" in result

    def test_returns_unavailable_message_if_empty(self, mocker, yf_ticker_mock):
        """Should return unavailable message if history is empty."""

        # Arrange: Setup mock with an empty history.
        historical_data = mocker.Mock()
        historical_data.empty = True
        yf_ticker_mock.history.return_value = historical_data

        # Act: Execute the function to get stock history.
        result = market_tools.get_stock_price_history.invoke({"ticker": "PETR4", "period": "1y"})

        # Assert: Verify that the unavailable message is returned.
        assert "Histórico de preços indisponível." in result


class TestGetCompanyNameFromTicker:
    """Tests for get_company_name_from_ticker function."""

    @pytest.mark.parametrize(
        "mock_info, expected_name",
        [
            ({"longName": "Petrobras S.A."}, "Petrobras S.A."),
            ({"shortName": "Petrobras"}, "Petrobras"),
            ({}, "Nome não disponível."),
        ],
    )
    def test_returns_company_name_scenarios(self, yf_ticker_mock, mock_info, expected_name):
        """Should return the best company name available or a default message."""

        # Arrange: Setup mock info with the specific scenario data.
        yf_ticker_mock.info = mock_info

        # Act: Execute the function to get the company name.
        result = market_tools.get_company_name_from_ticker.invoke({"ticker": "PETR4"})

        # Assert: Verify that the returned name matches our expectation for this scenario.
        assert result == expected_name
