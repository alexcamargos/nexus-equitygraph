"""Math tools for financial calculations."""

from typing import Dict

from langchain_core.tools import tool


@tool
def calculate_percentage_change(initial_value: float, final_value: float) -> str:
    """Calculates the percentage change between two values.

    Args:
        initial_value (float): The initial value.
        final_value (float): The final value.

    Returns:
        str: The percentage change as a string.

    Raises:
        ValueError: If initial_value is zero.
        TypeError: If inputs are not numbers.
        ZeroDivisionError: If final_value is zero.
    """

    try:
        if initial_value == 0:
            raise ValueError("Initial value is zero, calculation undefined.")

        change = ((final_value - initial_value) / initial_value) * 100

        return f"{change:+.2f}%"
    except (TypeError, ZeroDivisionError) as error:
        return f"Calculation error: {str(error)}"


@tool
def calculate_financial_ratios(
    net_income: float, equity: float, total_assets: float
) -> Dict[str, float]:
    """Calculates basic financial ratios: ROE and ROA.

    Args:
        net_income (float): Net Income.
        equity (float): Equity.
        total_assets (float): Total Assets.

    Returns:
        Dict[str, float]: Dictionary with ROE and ROA.

    Raises:
        TypeError: If any input is not a number.
    """

    if not all(
        isinstance(value, (int, float)) for value in (net_income, equity, total_assets)
    ):
        raise TypeError("All inputs must be numeric values.")

    return {
        "ROE": round((net_income / equity) * 100, 2) if equity else 0.0,
        "ROA": round((net_income / total_assets) * 100, 2) if total_assets else 0.0,
    }
