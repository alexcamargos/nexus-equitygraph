"""Tests for CVMAccountMapper in nexus_equitygraph.core.cvm_mapper."""

from datetime import datetime

import pandas as pd
import pytest

from nexus_equitygraph.services.cvm_mapper import CVMAccountMapper


class TestCVMAccountMapper:
    """Test suite for CVMAccountMapper."""

    @pytest.fixture
    def mapper(self, mock_cvm_data):
        """Fixture to create a CVMAccountMapper instance with mock data."""

        return CVMAccountMapper(mock_cvm_data)

    @pytest.fixture
    def empty_mapper(self):
        """Fixture that returns an empty CVMAccountMapper (no data)."""

        return CVMAccountMapper({})

    def test_initialization(self, mapper, mock_cvm_data):
        """Test that the mapper is initialized with the correct data."""

        # Assert: Verify that the mapper's data matches the mock data.
        assert mapper.data == mock_cvm_data

    def test_get_comparison_dates(self, mapper):
        """Test retrieval of comparison dates (LTM and previous years)."""

        # Act: Retrieve comparison dates.
        dates = mapper.get_comparison_dates()

        # Assert: Verify the returned periods and dates.
        assert len(dates) == 3
        assert "LTM" in dates[0][0]
        assert dates[0][1] is None
        assert dates[1][0] == "2022"
        assert dates[1][1] == datetime(2022, 12, 31)
        assert dates[2][0] == "2021"
        assert dates[2][1] == datetime(2021, 12, 31)

    def test_get_raw_value(self, mapper):
        """Test retrieval of raw values for a specific date."""

        # Arrange: Define reference dates.
        dt_2023 = datetime(2023, 12, 31)
        dt_2022 = datetime(2022, 12, 31)

        # Act: Retrieve raw values for specific dates.
        val_2023 = mapper.get_raw_value("DRE", "3.01", "Receita", dt_2023)
        val_2022 = mapper.get_raw_value("DRE", "3.01", "Receita", dt_2022)

        # Assert: Verify the retrieved values match the mock data.
        assert val_2023 == 1000.0
        assert val_2022 == 900.0

    @pytest.mark.parametrize(
        "method, expected",
        [
            ("get_net_income", 200.0),
            ("get_revenue", 1000.0),
            ("get_gross_profit", 500.0),
            ("get_ebit", 300.0),
            ("get_depreciation", -20.0),
            ("get_ebitda", 320.0),
            ("get_equity", 1000.0),
            ("get_total_assets", 2000.0),
            ("get_current_assets", 800.0),
            ("get_current_liabilities", 400.0),
            ("get_gross_debt", 200.0),
            ("get_cash_and_equivalents", 100.0),
            ("get_operating_cash_flow", 250.0),
            ("get_capex", -50.0),
            ("get_dividends_paid", 20.0),
            ("dva_personnel", 50.0),
            ("dva_taxes", 30.0),
            ("dva_lenders", 20.0),
            ("dva_shareholders", 200.0),
        ],
    )
    def test_financial_metrics(self, mapper, method, expected):
        """Test retrieval of various financial metrics."""

        # Act: Call the financial metric method dynamically.
        result = getattr(mapper, method)()

        # Assert: Verify the result matches the expected value.
        assert result == expected

    def test_get_net_income_with_date(self, mapper):
        """Test Net Income retrieval with specific date."""

        # Arrange: Define a specific reference date.
        dt_2022 = datetime(2022, 12, 31)

        # Act: Retrieve Net Income for the specific date.
        result = mapper.get_net_income(reference_date=dt_2022)

        # Assert: Verify the result matches the expected value for that date.
        assert result == 180.0

    def test_share_count(self, mapper):
        """Test Share Count property."""

        # Act: Access the share_count property.
        count = mapper.share_count

        # Assert: Verify the share count matches the mock data.
        assert count == 1000

    def test_missing_data_handling(self, empty_mapper):
        """Test handling of missing data."""

        # Act & Assert: Verify that methods return default values (0.0 or empty list) when data is missing.
        assert empty_mapper.get_revenue() == 0.0
        assert empty_mapper.get_net_income() == 0.0
        assert empty_mapper.share_count == 0
        assert empty_mapper.get_comparison_dates() == []

    def test_get_value_not_found(self, mapper):
        """Test _get_value returns 0.0 when account is not found."""

        # Arrange: Define a reference date.
        dt_2023 = datetime(2023, 12, 31)

        # Act: Attempt to retrieve a non-existent account.
        val = mapper.get_raw_value("DRE", "9.99", "NonExistent", dt_2023)

        # Assert: Verify the result is 0.0.
        assert val == 0.0

    def test_get_value_wrong_report_type(self, mapper):
        """Test _get_value returns 0.0 for wrong report type."""

        # Arrange: Define a reference date.
        dt_2023 = datetime(2023, 12, 31)

        # Act: Attempt to retrieve value from an invalid report type.
        val = mapper.get_raw_value("INVALID_TYPE", "3.01", "Receita", dt_2023)

        # Assert: Verify the result is 0.0.
        assert val == 0.0

    def test_filter_period_fallback_string_dt_refer(self, mock_cvm_data):
        """Test fallback to string comparison for DT_REFER filtering."""

        # Arrange: Prepare data with DT_REFER as strings instead of datetime objects.
        dt_2023 = datetime(2023, 12, 31)
        data = {k: v.copy() for k, v in mock_cvm_data.items()}
        data["DRE"] = data["DRE"].copy()
        data["DRE"]["DT_REFER"] = data["DRE"]["DT_REFER"].dt.strftime("%Y-%m-%d")
        mapper_local = CVMAccountMapper(data)

        # Act: Retrieve value using a datetime filter.
        value = mapper_local.get_raw_value("DRE", "3.01", "Receita", dt_2023)

        # Assert: Verify the value is retrieved correctly despite type mismatch.
        assert value == 1000.0

    def test_filter_accumulated_prefers_initial_period(self):
        """Test that the mapper prefers the correct accumulated period based on DT_INI_EXERC."""

        # Arrange: Create a DataFrame with multiple accumulation periods for the same date.
        dt = datetime(2023, 6, 30)
        df = pd.DataFrame(
            [
                {
                    "DT_REFER": dt,
                    "DT_INI_EXERC": "2023-01-01",
                    "CD_CONTA": "3.99",
                    "DS_CONTA": "TesteAcum",
                    "VL_CONTA": 123.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
                {
                    "DT_REFER": dt,
                    "DT_INI_EXERC": "2023-04-01",
                    "CD_CONTA": "3.99",
                    "DS_CONTA": "TesteAcum",
                    "VL_CONTA": 999.0,
                    "ORDEM_EXERC": "ÚLTIMO",
                },
            ]
        )
        mapper_local = CVMAccountMapper({"DRE": df})

        # Act: Retrieve the raw value (which forces accumulated filtering).
        value = mapper_local.get_raw_value("DRE", "3.99", "TesteAcum", dt)

        # Assert: Verify the value corresponds to the period starting at the beginning of the year.
        assert value == 123.0

    def test_filter_exercise_prefers_ultimo(self):
        """Test that the mapper filters for 'ÚLTIMO' exercise order."""

        # Arrange: Create a DataFrame with 'ÚLTIMO' and 'PENULTIMO' entries.
        dt_2023 = datetime(2023, 12, 31)
        df = pd.DataFrame(
            [
                {"DT_REFER": dt_2023, "CD_CONTA": "4.01", "DS_CONTA": "X", "VL_CONTA": 10.0, "ORDEM_EXERC": "PENULTIMO"},
                {"DT_REFER": dt_2023, "CD_CONTA": "4.01", "DS_CONTA": "X", "VL_CONTA": 20.0, "ORDEM_EXERC": "ÚLTIMO"},
            ]
        )
        mapper_local = CVMAccountMapper({"DRE": df})

        # Act: Retrieve the raw value.
        value = mapper_local.get_raw_value("DRE", "4.01", "X", dt_2023)

        # Assert: Verify the value corresponds to the 'ÚLTIMO' entry.
        assert value == 20.0

    def test_determine_report_date_invalid_max_returns_none(self):
        """Test that _determine_report_date returns None for invalid dates."""

        # Arrange: Create a DataFrame with an invalid date string.
        df = pd.DataFrame([{"DT_REFER": "invalid-date", "CD_CONTA": "1", "DS_CONTA": "x", "VL_CONTA": 1.0}])
        mapper_local = CVMAccountMapper({"DRE": df})

        # Act: Attempt to determine the report date.
        result = mapper_local._determine_report_date(df, None)

        # Assert: Verify the result is None.
        assert result is None

    def test_last_year_periods_handles_leap_year(self, mapper):
        """Test that _last_year_periods correctly handles leap years."""

        # Arrange: Define a leap year date (Feb 29).
        leap_date = datetime(2020, 2, 29)

        # Act: Calculate last year periods.
        last_year_end, last_year_same_period = mapper._last_year_periods(leap_date)

        # Assert: Verify the calculated dates handle the leap year correctly.
        assert last_year_end == datetime(2019, 12, 31)
        assert last_year_same_period == datetime(2019, 2, 28)
