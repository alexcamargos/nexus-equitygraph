"""Tests for financial_tools module."""

import pandas as pd
import pytest

from nexus_equitygraph.core.exceptions import IndicatorCalculationError
from nexus_equitygraph.services.cvm_mapper import CVMAccountMapper
from nexus_equitygraph.tools.financial_tools import get_financial_statements


class TestFinancialTools:
    """Test suite for financial tools."""

    @pytest.fixture
    def mock_mapper(self, mocker):
        """Fixture for CVMAccountMapper mock."""

        mapper = mocker.MagicMock()
        mapper.data = {}
        return mapper

    @pytest.fixture
    def populated_mapper(self, mock_cvm_data):
        """Fixture for a CVMAccountMapper instance populated with mock data."""

        return CVMAccountMapper(mock_cvm_data)

    def test_get_financial_statements_success(
        self,
        mocker,
        populated_mapper,
    ):
        """Test successful retrieval of financial statements."""

        # Arrange: Setup mocks for dependencies and return values.
        mocker.patch(
            "nexus_equitygraph.tools.financial_tools.get_account_mapper",
            return_value=populated_mapper,
        )
        mock_process_dre = mocker.patch("nexus_equitygraph.tools.financial_tools.process_and_format_dre_for_year")
        mock_process_bpp = mocker.patch("nexus_equitygraph.tools.financial_tools.process_and_format_bpp_for_year")
        mocker.patch(
            "nexus_equitygraph.tools.financial_tools.build_metadata",
            return_value="\n> Metadata",
        )

        # Arrange: Configure side effects for helper functions.
        mock_process_dre.side_effect = lambda df, year: [f"DRE {year}"]
        mock_process_bpp.side_effect = lambda mapper, year: [f"BPP {year}"]

        # Act: Call the function to get financial statements for 2 years.
        result = get_financial_statements.invoke({"ticker": "PETR4", "years_depth": 2})

        # Assert: Verify the formatted output contains expected sections for 2023 and 2022.
        assert "RELATÓRIO FINANCEIRO HISTÓRICO: PETR4" in result
        assert "--- Exercício 2023 ---" in result
        assert "DRE 2023" in result
        assert "BPP 2023" in result
        assert "--- Exercício 2022 ---" in result
        assert "DRE 2022" in result
        assert "BPP 2022" in result
        assert "> Metadata" in result

        # Assert: Verify helper functions were called correctly.
        assert mock_process_dre.call_count == 2
        assert mock_process_bpp.call_count == 2

    def test_get_financial_statements_no_dre(self, mocker, mock_mapper):
        """Test behavior when DRE data is missing."""

        # Arrange: Setup mocks with empty data.
        mocker.patch(
            "nexus_equitygraph.tools.financial_tools.get_account_mapper",
            return_value=mock_mapper,
        )
        mock_mapper.data = {}  # Empty data

        # Act: Call the function.
        result = get_financial_statements.invoke({"ticker": "PETR4"})

        # Assert: Check for error message.
        assert result == "Dados DRE não encontrados."

    def test_get_financial_statements_empty_dre(self, mocker, mock_mapper):
        """Test behavior when DRE DataFrame is empty."""

        # Arrange: Setup mocks with empty DataFrame.
        mocker.patch(
            "nexus_equitygraph.tools.financial_tools.get_account_mapper",
            return_value=mock_mapper,
        )
        mock_mapper.data = {"DRE": pd.DataFrame()}  # Empty DataFrame

        # Act: Call the function.
        result = get_financial_statements.invoke({"ticker": "PETR4"})

        # Assert: Check for error message.
        assert result == "Dados DRE não encontrados."

    def test_get_financial_statements_missing_bpp(self, mocker, mock_cvm_data):
        """Test behavior when BPP data is missing (should still return DRE)."""

        # Arrange: Use mock data but remove the BPP key.
        del mock_cvm_data["BPP"]
        mapper_without_bpp = CVMAccountMapper(mock_cvm_data)

        mocker.patch(
            "nexus_equitygraph.tools.financial_tools.get_account_mapper",
            return_value=mapper_without_bpp,
        )
        mock_process_dre = mocker.patch(
            "nexus_equitygraph.tools.financial_tools.process_and_format_dre_for_year",
            return_value=["DRE Data"],
        )
        mock_process_bpp = mocker.patch("nexus_equitygraph.tools.financial_tools.process_and_format_bpp_for_year")
        mocker.patch("nexus_equitygraph.tools.financial_tools.build_metadata", return_value="")

        # Act: Call the function.
        result = get_financial_statements.invoke({"ticker": "PETR4"})

        # Assert: Verify DRE data is present and BPP processing was skipped.
        assert "DRE Data" in result
        assert mock_process_dre.called
        assert not mock_process_bpp.called

    def test_get_financial_statements_years_depth(self, mocker, populated_mapper):
        """Test that years_depth limits the output."""

        # Arrange: Setup mocks with data from conftest.
        mocker.patch(
            "nexus_equitygraph.tools.financial_tools.get_account_mapper",
            return_value=populated_mapper,
        )
        mock_process_dre = mocker.patch(
            "nexus_equitygraph.tools.financial_tools.process_and_format_dre_for_year",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.financial_tools.process_and_format_bpp_for_year",
            return_value=[],
        )
        mocker.patch("nexus_equitygraph.tools.financial_tools.build_metadata", return_value="")

        # Act: Request only 1 year of data.
        get_financial_statements.invoke({"ticker": "PETR4", "years_depth": 1})

        # Assert: Verify that only the most recent year (2023) was processed.
        assert mock_process_dre.call_count == 1
        args, _ = mock_process_dre.call_args
        # args[1] is year
        assert args[1] == "2023"

    def test_get_financial_statements_exception(self, mocker):
        """Test exception handling via decorator."""

        # Arrange: Simulate an error in the dependency.
        mocker.patch(
            "nexus_equitygraph.tools.financial_tools.get_account_mapper",
            side_effect=ValueError("Simulated error"),
        )

        # Act & Assert: Verify that the decorator raises IndicatorCalculationError.
        with pytest.raises(IndicatorCalculationError) as excinfo:
            get_financial_statements.invoke({"ticker": "PETR4"})

        # Assert: Check exception message.
        assert "Erro no cálculo de demonstrações financeiras" in str(excinfo.value)
        assert "Simulated error" in str(excinfo.value)
