"""Tests for the CVM parser service."""

import io

import pandas as pd
import pytest

from nexus_equitygraph.services.cvm_parser import (
    _filter_company_data,
    _process_numeric_columns,
    _read_csv_robust,
    append_report_data,
    extract_years_from_html,
    parse_cadastral_csv,
    parse_report_zip,
)


class TestCVMParser:
    """Tests for the CVM parser service."""

    @pytest.fixture
    def sample_report_df(self):
        """Fixture providing a sample report DataFrame for testing."""

        return pd.DataFrame(
            {
                "CD_CVM": ["001234", "005678"],
                "CNPJ_CIA": ["11.111.111/0001-11", "22.222.222/0001-22"],
                "VL_CONTA": ["1.234,56", "1000,00"],
                "ESCALA_MOEDA": ["MIL", "UNIDADE"],
                "DADO": ["A", "B"],
            }
        )

    @pytest.fixture
    def sample_cvm_html(self):
        """Fixture providing sample HTML content from CVM portal."""

        return b"""
        <html>
            <a href="itr_cia_aberta_2023.zip">2023</a>
            <a href="itr_cia_aberta_2021.zip">2021</a>
            <a href="other_file.zip">Other</a>
            <a href="itr_cia_aberta_2022.zip">2022</a>
        </html>
        """

    def test_process_numeric_columns_scaling(self, sample_report_df):
        """Tests if numeric columns are processed and scaled correctly."""

        # Action: Process numeric columns in the sample DataFrame.
        _process_numeric_columns(sample_report_df, "test.csv")

        # Assert: Verify that values are correctly converted and scaled based on currency scale.
        assert sample_report_df.loc[0, "VL_CONTA"] == 1234560.0
        assert sample_report_df.loc[1, "VL_CONTA"] == 1000.0

    def test_filter_company_data_cvm_code(self, sample_report_df):
        """Tests if company filtering by CVM code works correctly."""

        # Action: Filter the report DataFrame by CVM code.
        filtered = _filter_company_data(
            sample_report_df, "1234", None, "file.csv", "ITR"
        )

        # Assert: Verify that only the matching company record is returned.
        assert len(filtered) == 1
        assert filtered.iloc[0]["DADO"] == "A"

    def test_filter_company_data_no_match(self, sample_report_df):
        """Tests if filtering returns empty DF when no match is found."""

        # Action: Filter the report DataFrame with non-matching criteria.
        filtered = _filter_company_data(
            sample_report_df, "9999", "00.000.000/0000-00", "file.csv", "ITR"
        )

        # Assert: Verify that an empty DataFrame is returned.
        assert filtered.empty

    def test_filter_company_data_cnpj(self, sample_report_df):
        """Tests if company filtering by CNPJ works correctly."""

        # Action: Filter the report DataFrame by CNPJ.
        filtered = _filter_company_data(
            sample_report_df, "0", "11.111.111/0001-11", "file.csv", "ITR"
        )

        # Assert: Verify that the correct company record is identified.
        assert len(filtered) == 1
        assert filtered.iloc[0]["DADO"] == "A"

    def test_read_csv_robust_encoding(self):
        """Tests if CSV reading handles different encodings."""

        # Setup: Create binary CSV content with specific encoding.
        content = "COL1;COL2\nVAL1;VAL2".encode("ISO-8859-1")
        # Action: Read the CSV content robustly.
        df = _read_csv_robust(io.BytesIO(content))

        # Assert: Verify that the DataFrame is correctly loaded.
        assert not df.empty
        assert df.iloc[0]["COL1"] == "VAL1"

    def test_parse_cadastral_csv_empty(self):
        """Tests parsing of empty cadastral content."""

        # Action & Assert: Verify that parsing empty or null content returns an empty DataFrame.
        assert parse_cadastral_csv(b"").empty
        assert parse_cadastral_csv(None).empty

    def test_parse_report_zip_corrupted(self):
        """Tests handling of corrupted ZIP files."""

        # Action: Attempt to parse a corrupted ZIP file.
        res = parse_report_zip(
            b"not a zip content",
            "1234",
            None,
            2023,
            ["BPA"],
            file_prefix="prefix",
            source_tag="ITR",
            consolidated=True,
        )

        # Assert: Verify that an empty dictionary is returned without raising errors.
        assert res == {}

    def test_extract_years_from_html(self, sample_cvm_html):
        """Tests if years are extracted correctly from HTML content."""

        # Action: Extract years from the sample HTML content.
        years = extract_years_from_html(sample_cvm_html)

        # Assert: Verify that the years are extracted and sorted correctly.
        assert years == [2023, 2022, 2021]

    def test_extract_years_from_html_empty(self):
        """Tests year extraction from empty or invalid HTML."""

        # Action & Assert: Verify that extracting from empty or invalid HTML returns an empty list.
        assert extract_years_from_html(b"<html></html>") == []
        assert extract_years_from_html(b"") == []

    def test_append_report_data(self, sample_report_df):
        """Tests if report data is appended correctly."""

        # Setup: Prepare existing consolidated data and new report data.
        consolidated = {"BPA": sample_report_df.head(1).copy()}
        new_data = {
            "BPA": sample_report_df.tail(1).copy(),
            "BPP": pd.DataFrame(
                {"VAL": [30]}
            ),
        }

        # Action: Append the new data to the consolidated dictionary.
        append_report_data(consolidated, new_data)

        # Assert: Verify that the data is correctly merged.
        assert len(consolidated["BPA"]) == 2
        assert "BPP" not in consolidated
