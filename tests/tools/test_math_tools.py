"""Tests for math_tools in nexus_equitygraph.tools.math_tools."""

import pytest
from pydantic import ValidationError

from nexus_equitygraph.tools.math_tools import calculate_financial_ratios, calculate_percentage_change


class TestCalculatePercentageChange:
    """Test suite for calculate_percentage_change function."""

    @pytest.mark.parametrize(
        ("initial_value", "final_value", "expected"),
        [
            (100.0, 150.0, "+50.00%"),  # positive change
            (100.0, 75.0, "-25.00%"),  # negative change
            (100.0, 100.0, "+0.00%"),  # no change
            (50, 100, "+100.00%"),  # integer inputs
            (0.01, 0.02, "+100.00%"),  # small decimals
            (10.0, 1_000.0, "+9900.00%"),  # large change
            (-100.0, -50.0, "-50.00%"),  # negative values
        ],
        ids=[
            "positive_change",
            "negative_change",
            "no_change",
            "integer_inputs",
            "small_decimals",
            "large_change",
            "negative_values",
        ],
    )
    def test_percentage_change_calculation(self, initial_value, final_value, expected):
        """Should calculate percentage change correctly for various inputs."""

        # Act: Call the function with test inputs.
        result = calculate_percentage_change.invoke({"initial_value": initial_value, "final_value": final_value})

        # Assert: Check the result matches expected value.
        assert result == expected

    def test_zero_initial_value_raises_error(self):
        """Should raise ValueError when initial value is zero."""

        # Arrange: Prepare input with zero initial value.
        invalid_input = {"initial_value": 0.0, "final_value": 100.0}

        # Act & Assert: Check that ValueError is raised for zero initial value.
        with pytest.raises(ValueError, match="Initial value is zero"):
            calculate_percentage_change.invoke(invalid_input)

    def test_type_error_returns_error_message(self):
        """Should return error message when TypeError occurs in calculation."""

        # Arrange: Get the underlying function bypassing Pydantic validation.
        func = getattr(calculate_percentage_change, "func")

        # Act: Call the function directly with invalid input types.
        result = func("not_a_number", 100.0)

        # Assert: Check that the result contains an error message.
        assert "Calculation error:" in result


class TestCalculateFinancialRatios:
    """Test suite for calculate_financial_ratios function."""

    @pytest.mark.parametrize(
        ("net_income", "equity", "total_assets", "expected_roe", "expected_roa"),
        [
            (100_000.0, 500_000.0, 1_000_000.0, 20.0, 10.0),  # valid inputs
            (100_000.0, 0.0, 1_000_000.0, 0.0, 10.0),  # zero equity
            (100_000.0, 500_000.0, 0.0, 20.0, 0.0),  # zero total assets
            (0.0, 500_000.0, 1_000_000.0, 0.0, 0.0),  # zero net income
            (-50_000.0, 500_000.0, 1_000_000.0, -10.0, -5.0),  # negative net income
            (10_000, 100_000, 200_000, 10.0, 5.0),  # integer inputs
            (33_333.0, 100_000.0, 100_000.0, 33.33, 33.33),  # rounding precision
            (0.0, 0.0, 0.0, 0.0, 0.0),  # all zeros
        ],
        ids=[
            "valid_inputs",
            "zero_equity",
            "zero_total_assets",
            "zero_net_income",
            "negative_net_income",
            "integer_inputs",
            "rounding_precision",
            "all_zeros",
        ],
    )
    def test_financial_ratios_calculation(self, net_income, equity, total_assets, expected_roe, expected_roa):
        """Should calculate ROE and ROA correctly for various inputs."""

        # Act: Call the function with test inputs.
        result = calculate_financial_ratios.invoke(
            {"net_income": net_income, "equity": equity, "total_assets": total_assets}
        )

        # Assert: Check the results match expected values.
        assert result["ROE"] == expected_roe
        assert result["ROA"] == expected_roa

    @pytest.mark.parametrize(
        "invalid_input",
        [
            {"net_income": "invalid", "equity": 500_000.0, "total_assets": 1_000_000.0},
            {"net_income": None, "equity": 500_000.0, "total_assets": 1_000_000.0},
        ],
        ids=["string_input", "none_input"],
    )
    def test_invalid_input_raises_validation_error(self, invalid_input):
        """Should raise ValidationError for non-numeric inputs."""

        # Act & Assert: Check that ValidationError is raised for invalid inputs.
        with pytest.raises(ValidationError):
            calculate_financial_ratios.invoke(invalid_input)

    def test_direct_call_with_invalid_type_raises_type_error(self):
        """Should raise TypeError when function is called directly with invalid types."""

        # Arrange: Get the underlying function bypassing Pydantic validation.
        func = getattr(calculate_financial_ratios, "func")

        # Act & Assert: Call the function directly and check TypeError.
        with pytest.raises(TypeError, match="All inputs must be numeric values"):
            func("invalid", 500_000.0, 1_000_000.0)
