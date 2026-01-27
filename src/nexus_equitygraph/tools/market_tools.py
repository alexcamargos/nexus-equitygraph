"""Market tools for fetching stock data using yfinance."""

import yfinance as yf
from langchain_core.tools import tool

from nexus_equitygraph.core.exceptions import handle_indicator_exceptions
from nexus_equitygraph.tools.helpers import (
    build_metadata,
    calculate_price_range,
    calculate_rsi,
    calculate_sma_status,
    calculate_volatility,
    determine_general_trend,
    determine_trend,
    ensure_sa_suffix,
)


@tool
@handle_indicator_exceptions("preço atual")
def get_current_stock_price(ticker: str) -> float:
    """Fetches the current stock price for a given ticker.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        float: The current stock price.
    """
    yf_symbol = ensure_sa_suffix(ticker)
    yf_ticker = yf.Ticker(yf_symbol)

    # Try different fields for current price.
    price = (
        yf_ticker.info.get("currentPrice")
        or yf_ticker.info.get("regularMarketPrice")
        or yf_ticker.info.get("ask")
        or yf_ticker.info.get("previousClose")
    )

    if price is None:
        # Fallback to history if info fails
        hist = yf_ticker.history(period="1d")
        if not hist.empty:
            price = hist["Close"].iloc[-1]

    return float(price) if price else 0.0


@tool
@handle_indicator_exceptions("mercado")
def get_stock_price_history(ticker: str, period: str = "1y") -> str:
    """Fetches the stock price history for a given ticker.

    Args:
        ticker (str): The company ticker (e.g., PETR4).
        period (str): The period for the history
                      (e.g., '1d', '5d', '1mo', '3mo', '6mo',
                      '1y', '2y', '5y', '10y', 'ytd', 'max').

    Returns:
        str: The formatted stock price history.
    """

    summary = ["Dados de Mercado (Source: Yahoo Finance):"]

    yf_symbol = ensure_sa_suffix(ticker)
    yf_ticker = yf.Ticker(yf_symbol)
    price_history = yf_ticker.history(period=period)

    if price_history.empty:
        return "Histórico de preços indisponível."

    current_price = price_history['Close'].iloc[-1]

    # Append calculated indicators to summary.
    summary.append(calculate_sma_status(price_history, current_price, 50))
    summary.append(calculate_sma_status(price_history, current_price, 200))
    summary.append(calculate_rsi(price_history))
    summary.append(calculate_volatility(price_history))
    summary.append(calculate_price_range(price_history))
    summary.append(determine_trend(price_history, 5))
    summary.append(determine_general_trend(price_history))

    footer = build_metadata(sources=["Yahoo Finance"], periods=[period])

    return "\n".join(summary) + footer


@tool
@handle_indicator_exceptions("nome da empresa")
def get_company_name_from_ticker(ticker: str) -> str:
    """Fetches the company name for a given ticker.

    Args:
        ticker (str): The company ticker (e.g., PETR4).

    Returns:
        str: The company name.
    """
    yf_symbol = ensure_sa_suffix(ticker)
    yf_ticker = yf.Ticker(yf_symbol)
    yf_info = yf_ticker.info

    name = yf_info.get("longName") or yf_info.get("shortName") or yf_info.get("companyName") or yf_info.get("name")

    return str(name) if name else "Nome não disponível."
