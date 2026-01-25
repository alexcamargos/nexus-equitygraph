"""CVM Account Mapper for financial data extraction."""

from datetime import datetime
from typing import Optional

import pandas as pd


class CVMAccountMapper:
    """Helper class to map and extract standardized financial accounts from CVM DataFrames (ITR/DFP)."""

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        """Initializes the mapper with consolidated CVM data.

        Args:
            data (dict[str, pd.DataFrame]): Consolidated CVM data by report type.
        """

        self.data = data

    # -- Helpers methods for getting values calculations --
    def _get_financial_df(self, report_type: str) -> pd.DataFrame:
        """Retrieves the DataFrame for a specific financial report type.

        Args:
            report_type (str): Type of financial report ('DRE', etc.).

        Returns:
            pd.DataFrame: The DataFrame for the specified report type.
        """

        if report_type not in self.data:
            return pd.DataFrame()

        report_df = self.data[report_type]
        if report_df is None or report_df.empty:
            return pd.DataFrame()

        return report_df

    def _filter_period(self, data_frame: pd.DataFrame, date_filter: Optional[datetime]) -> pd.DataFrame:
        """Filters the DataFrame by the reference date.

        Args:
            data_frame (pd.DataFrame): The DataFrame to filter.
            date_filter (Optional[datetime]): The reference date to filter by.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """

        if data_frame.empty:
            return data_frame

        if date_filter is not None:
            reference_date_column = data_frame["DT_REFER"]

            # If column already datetime-like, compare directly.
            reference_date_dtype = reference_date_column.dtype
            if pd.api.types.is_datetime64_any_dtype(reference_date_dtype) or isinstance(
                reference_date_dtype, pd.DatetimeTZDtype
            ):
                return data_frame[reference_date_column == date_filter]

            # Try to parse the column to datetimes when possible and compare directly.
            try:
                parsed_dates = pd.to_datetime(reference_date_column, errors="coerce")
                if parsed_dates.notna().any():
                    return data_frame[parsed_dates == pd.to_datetime(date_filter)]
            except (TypeError, ValueError, OverflowError):
                pass

            # Fallback: compare string representations of dates.
            return data_frame[reference_date_column.astype(str) == date_filter.strftime("%Y-%m-%d")]

        return data_frame[data_frame["DT_REFER"] == data_frame["DT_REFER"].max()]

    def _filter_accumulated(self, data_frame: pd.DataFrame, force_accumulated: bool) -> pd.DataFrame:
        """Filters the DataFrame to only include accumulated periods if required.

        Args:
            data_frame (pd.DataFrame): The DataFrame to filter.
            force_accumulated (bool): Whether to enforce accumulated period filtering.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """

        if not force_accumulated or data_frame.empty or "DT_INI_EXERC" not in data_frame.columns:
            return data_frame

        try:
            reference_date_string = str(data_frame.iloc[0]["DT_REFER"])
            reference_year = reference_date_string[:4]
            initial_year_date = f"{reference_year}-01-01"
            initial_period_mask = data_frame["DT_INI_EXERC"].astype(str) == initial_year_date

            if initial_period_mask.any():
                return data_frame[initial_period_mask]

        except (ValueError, IndexError):
            pass

        return data_frame

    def _filter_exercise(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Filters the DataFrame for 'ÚLTIMO' exercise if applicable.

        Args:
            data_frame (pd.DataFrame): The DataFrame to filter.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """

        if data_frame.empty or "ORDEM_EXERC" not in data_frame.columns:
            return data_frame

        current_exercise_mask = data_frame["ORDEM_EXERC"].astype(str).str.upper().str.strip() == "ÚLTIMO"
        if current_exercise_mask.any():
            return data_frame[current_exercise_mask]

        return data_frame

    def _find_value(
        self, data_frame: pd.DataFrame, cd_conta_start: str, ds_conta_contains: Optional[str]
    ) -> Optional[float]:
        """Finds the value by account code or description.

        Args:
            data_frame (pd.DataFrame): The DataFrame to search in.
            cd_conta_start (str): The starting string of the account code.
            ds_conta_contains (Optional[str]): A substring that should be contained in the account description

        Returns:
            Optional[float]: The value if found, None otherwise.
        """

        if data_frame.empty:
            return None

        if cd_conta_start:
            account_codes = data_frame["CD_CONTA"].astype(str)

            matching_records = data_frame[account_codes.str.startswith(cd_conta_start, na=False)]
            if not matching_records.empty:
                return float(matching_records.iloc[0]["VL_CONTA"])

        if ds_conta_contains:
            account_descriptions = data_frame["DS_CONTA"].astype(str)

            matching_records = data_frame[account_descriptions.str.contains(ds_conta_contains, case=False, na=False)]
            if not matching_records.empty:
                return float(matching_records.iloc[0]["VL_CONTA"])

        return None

    def _get_value(
        self,
        report_type: str,
        cd_conta_start: str,
        ds_conta_contains: Optional[str] = None,
        date_filter: Optional[datetime] = None,
        force_accumulated: bool = False,
    ) -> float:
        """Retrieves the value of a specific account.

        Args:
            report_type (str): Type of financial report ('DRE', etc.).
            cd_conta_start (str): The starting string of the account code.
            ds_conta_contains (Optional[str]): A substring that should be contained in the account description.
            date_filter (Optional[datetime]): The reference date to filter by.
            force_accumulated (bool): Whether to enforce accumulated period filtering.

        Returns:
            float: The account value or 0.0 if not found.
        """

        financial_dataframe = self._get_financial_df(report_type)
        if financial_dataframe.empty:
            return 0.0

        financial_dataframe = self._filter_period(financial_dataframe, date_filter)
        if financial_dataframe.empty:
            return 0.0

        financial_dataframe = self._filter_accumulated(financial_dataframe, force_accumulated)
        financial_dataframe = self._filter_exercise(financial_dataframe)
        account_value = self._find_value(financial_dataframe, cd_conta_start, ds_conta_contains)

        return account_value if account_value is not None else 0.0

    # -- Helpers methods for LTM calculations --
    def _determine_report_date(
        self, data_frame: pd.DataFrame, reference_date: Optional[datetime]
    ) -> Optional[datetime]:
        """Determines the report date to use (explicit or latest in DataFrame).

        Args:
            data_frame (pd.DataFrame): The DataFrame to use.
            reference_date (Optional[datetime]): The reference date to use.
        Returns:
            Optional[datetime]: The determined report date.
        """

        if reference_date:
            return reference_date

        try:
            max_date_str = data_frame["DT_REFER"].max()

            return pd.to_datetime(max_date_str)
        except (ValueError, TypeError):
            return None

    def _accumulated_value_for_date(
        self, report_type: str, cd_conta_start: str, ds_conta_contains: Optional[str], date: datetime
    ) -> float:
        """Wrapper to fetch accumulated value for a given date.

        Args:
            report_type (str): Type of financial report ('DRE', etc.).
            cd_conta_start (str): The starting string of the account code.
            ds_conta_contains (Optional[str]): A substring that should be contained in the account description.
            date (datetime): The reference date to filter by.

        Returns:
            float: The accumulated account value or 0.0 if not found.
        """

        return self._get_value(report_type, cd_conta_start, ds_conta_contains, date_filter=date, force_accumulated=True)

    def _last_year_periods(self, current_report_date: datetime) -> tuple[datetime, datetime]:
        """Returns (last_year_end, last_year_same_period) handling leap years.

        Args:
            current_report_date (datetime): The current report date.

        Returns:
            tuple[datetime, datetime]: (last_year_end, last_year_same_period)
        """

        last_year = current_report_date.year - 1
        last_year_end = datetime(last_year, 12, 31)

        try:
            last_year_same_period = current_report_date.replace(year=last_year)
        except ValueError:
            last_year_same_period = current_report_date.replace(year=last_year, day=28)

        return last_year_end, last_year_same_period

    def _get_ltm_value(
        self,
        report_type: str,
        cd_conta_start: str,
        ds_conta_contains: Optional[str] = None,
        reference_date: Optional[datetime] = None,
    ) -> float:
        """Calculates LTM (Last Twelve Months) value.

        Formula: Current Accumulated + Last Year Annual - Last Year Accumulated (Same Period).
        """
        financial_dataframe = self._get_financial_df(report_type)
        if financial_dataframe.empty:
            return 0.0

        current_report_date = self._determine_report_date(financial_dataframe, reference_date)
        if current_report_date is None:
            return 0.0

        # Current Accumulated Value
        current_accumulated_value = self._accumulated_value_for_date(
            report_type, cd_conta_start, ds_conta_contains, current_report_date
        )

        # If it's year-end (Dec 31), LTM is the annual value itself
        if current_report_date.month == 12 and current_report_date.day == 31:
            return current_accumulated_value

        # Last-year periods
        last_year_end, last_year_same_period = self._last_year_periods(current_report_date)

        last_year_annual_value = self._accumulated_value_for_date(
            report_type, cd_conta_start, ds_conta_contains, last_year_end
        )

        last_period_accumulated_value = self._accumulated_value_for_date(
            report_type, cd_conta_start, ds_conta_contains, last_year_same_period
        )

        return current_accumulated_value + last_year_annual_value - last_period_accumulated_value

    def get_comparison_dates(self) -> list[tuple[str, Optional[datetime]]]:
        """Returns a list of periods for historical comparison (LTM, Year-1, Year-2).

        Returns:
            list[tuple[str, Optional[datetime]]]: List of (label, date) tuples
        """

        periods = []
        reference_date = None

        if "DRE" in self.data and not self.data["DRE"].empty:
            reference_date = pd.to_datetime(self.data["DRE"]["DT_REFER"].max())
        elif "BPA" in self.data and not self.data["BPA"].empty:
            reference_date = pd.to_datetime(self.data["BPA"]["DT_REFER"].max())

        if reference_date:
            periods.append((f"LTM ({reference_date.strftime('%d/%m/%Y')})", None))

            current_year = reference_date.year
            previous_year = current_year - 1

            periods.append((f"{previous_year}", datetime(previous_year, 12, 31)))

            year_before_previous = current_year - 2

            periods.append((f"{year_before_previous}", datetime(year_before_previous, 12, 31)))

        return periods

    def get_raw_value(
        self,
        report_type: str,
        cd_conta: str,
        ds_conta: str,
        reference_date: datetime,
    ) -> float:
        """Public wrapper to retrieve a raw value for a specific date (Point-in-Time).

        Useful for evolution charts where LTM calculation is not desired.

        Args:
            report_type (str): Type of report ('DRE', etc.).
            cd_conta (str): Account code.
            ds_conta (str): Account description.
            reference_date (datetime): Specific date to filter by.

        Returns:
            float: The account value or 0.0 if not found.
        """

        return self._get_value(report_type, cd_conta, ds_conta, date_filter=reference_date, force_accumulated=True)

    # --- Income Statement Metrics ---

    def get_net_income(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the net income (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The net income value or 0.0 if not found.
        """

        return self._get_ltm_value("DRE", "3.11", "Lucro", reference_date=reference_date)

    def get_revenue(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the revenue (LTM).
        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The revenue value or 0.0 if not found.
        """

        return self._get_ltm_value("DRE", "3.01", "Receita", reference_date=reference_date)

    def get_gross_profit(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the gross profit (LTM).
        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The gross profit value or 0.0 if not found.
        """

        return self._get_ltm_value("DRE", "3.03", "Resultado Bruto", reference_date=reference_date)

    def get_ebit(self, reference_date: Optional[datetime] = None) -> float:
        return self._get_ltm_value("DRE", "3.05", "Resultado Antes", reference_date=reference_date)

    def get_depreciation(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the depreciation (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The depreciation value or 0.0 if not found.
        """

        # Usually in DVA or DFC (Indirect Method)

        return self._get_value("DVA", "1.03", "Depreciação", date_filter=reference_date, force_accumulated=True)

    def get_ebitda(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the EBITDA (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The EBITDA value or 0.0 if not found.
        """

        ebit = self.get_ebit(reference_date)
        depreciation_amount = self.get_depreciation(reference_date)

        return ebit + abs(depreciation_amount) if depreciation_amount else ebit

    # --- Balance Sheet Metrics ---

    def get_equity(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the equity (LTM).
        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The equity value or 0.0 if not found.
        """

        return self._get_value("BPP", "2.03", "Patrimônio Líquido", date_filter=reference_date)

    def get_total_assets(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the total assets (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The total assets value or 0.0 if not found.
        """

        return self._get_value("BPA", "1", "Ativo Total", date_filter=reference_date)

    def get_current_assets(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the current assets (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The current assets value or 0.0 if not found.
        """

        return self._get_value("BPA", "1.01", "Ativo Circulante", date_filter=reference_date)

    def get_current_liabilities(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the current liabilities (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The current liabilities value or 0.0 if not found.
        """

        return self._get_value("BPP", "2.01", "Passivo Circulante", date_filter=reference_date)

    def get_gross_debt(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the gross debt (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The gross debt value or 0.0 if not found.
        """

        short_term_loans = self._get_value("BPP", "2.01.04", "Empréstimos", date_filter=reference_date)
        long_term_loans = self._get_value("BPP", "2.02.01", "Empréstimos", date_filter=reference_date)

        return short_term_loans + long_term_loans

    def get_cash_and_equivalents(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the cash and equivalents (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The cash and equivalents value or 0.0 if not found.
        """

        return self._get_value("BPA", "1.01.01", "Caixa", date_filter=reference_date)

    # -- Cash Flow Statement Metrics ---

    def get_operating_cash_flow(self) -> float:
        """Returns the operating cash flow (LTM).

        Returns:
            float: The operating cash flow value or 0.0 if not found.
        """

        # 6.01 - Net Cash from Operating Activities
        operating_cash_flow_value = self._get_value("DFC_MI", "6.01", "Operacionais")
        if operating_cash_flow_value == 0:
            operating_cash_flow_value = self._get_value("DFC_MD", "6.01", "Operacionais")

        return operating_cash_flow_value

    def get_capex(self) -> float:
        """Returns the capital expenditures (CAPEX) (LTM).

        Returns:
            float: The CAPEX value or 0.0 if not found.
        """

        # 6.02 - Net Cash from Investing Activities (Proxy for CAPEX)
        capex_data_type = "DFC_MI" if "DFC_MI" in self.data else "DFC_MD"

        return self._get_value(capex_data_type, "6.02", "Investimento")

    def get_dividends_paid(self) -> float:
        """Returns the dividends paid (LTM).

        Returns:
            float: The dividends paid value or 0.0 if not found.
        """

        # 6.03 - Net Cash from Financing Activities
        cashflow_dividend_type = "DFC_MI" if "DFC_MI" in self.data else "DFC_MD"
        dividends_paid = self._get_value(cashflow_dividend_type, "", "Dividendos Pagos")
        if dividends_paid == 0:
            dividends_paid = self._get_value(cashflow_dividend_type, "", "Juros sobre Capital")

        return abs(dividends_paid)

    # -- DVA Breakdown Metrics ---

    def dva_personnel(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the personnel expenses from the DVA (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The personnel expenses value or 0.0 if not found.
        """

        return self._get_value("DVA", "7.02", "Pessoal", date_filter=reference_date)

    def dva_taxes(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the taxes from the DVA (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The taxes value or 0.0 if not found.
        """

        return self._get_value("DVA", "7.03", "Impostos", date_filter=reference_date)

    def dva_lenders(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the lenders expenses from the DVA (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The lenders expenses value or 0.0 if not found.
        """

        return self._get_value("DVA", "7.04", "Terceiros", date_filter=reference_date)

    def dva_shareholders(self, reference_date: Optional[datetime] = None) -> float:
        """Returns the shareholders expenses from the DVA (LTM).

        Args:
            reference_date (Optional[datetime]): Reference date for calculation. Defaults to latest.

        Returns:
            float: The shareholders expenses value or 0.0 if not found.
        """

        return self._get_value("DVA", "7.05", "Próprio", date_filter=reference_date)

    # -- Additional Metrics ---

    @property
    def share_count(self) -> int:
        """Returns the total number of shares (ON + PN).

        Returns:
            int: The total number of shares or 0 if not found.
        """

        if "composicao_capital" not in self.data:
            return 0

        capital_composition_df = self.data["composicao_capital"]
        if capital_composition_df.empty or "QT_TOTAL" not in capital_composition_df.columns:
            return 0

        last_date = capital_composition_df["DT_REFER"].max()
        current_share_row = capital_composition_df[capital_composition_df["DT_REFER"] == last_date]
        if current_share_row.empty:
            return 0

        try:
            return int(current_share_row.iloc[0]["QT_TOTAL"])
        except (ValueError, TypeError):
            return 0
