"""Custom exceptions for the nexus-equitygraph package."""

from functools import wraps
from typing import Callable, TypeVar

import requests
from loguru import logger

# Type variable for generic return type
T = TypeVar("T")


class NexusEquityGraphError(Exception):
    """Base exception for all nexus-equitygraph errors."""


class CVMDataError(NexusEquityGraphError):
    """Exception raised when CVM data retrieval or processing fails."""


class IndicatorCalculationError(NexusEquityGraphError):
    """Exception raised when financial indicator calculation fails."""


class CompanyNotFoundError(CVMDataError):
    """Exception raised when a company is not found in CVM registry."""


class InsufficientDataError(CVMDataError):
    """Exception raised when there is insufficient data for calculation."""


def handle_indicator_exceptions(operation_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that provides standardized exception handling for indicator tools.

    This decorator eliminates repetitive try/except blocks across indicator functions
    by centralizing exception handling logic.

    Args:
        operation_name: Human-readable name of the operation (e.g., "valuation", "eficiência").

    Returns:
        Decorated function with standardized exception handling.

    Example:
        @tool
        @handle_indicator_exceptions("valuation")
        def calculate_valuation_indicators(ticker: str, current_price: float) -> str:
            # Implementation without try/except boilerplate
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Extract ticker from args or kwargs for error messages
            ticker = kwargs.get("ticker") or (args[0] if args else "unknown")

            try:
                return func(*args, **kwargs)

            except (KeyError, ValueError, TypeError, ZeroDivisionError) as error:
                logger.exception(f"Calculation error for {ticker}")
                raise IndicatorCalculationError(
                    f"Erro no cálculo de {operation_name} para {ticker}: {error}"
                ) from error

            except requests.RequestException as error:
                logger.exception(f"Network error fetching data for {ticker}")
                raise CVMDataError(f"Erro de rede ao buscar dados para {ticker}: {error}") from error

            except (IndicatorCalculationError, CVMDataError):
                raise

            except Exception as error:  # pylint: disable=broad-exception-caught
                logger.exception(f"Unexpected error in {operation_name} for {ticker}")
                return f"Erro {operation_name}: {str(error)}"  # type: ignore[return-value]

        return wrapper

    return decorator
