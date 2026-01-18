"""Tests for the CVM Registry service."""

import pandas as pd
import pytest

from nexus_equitygraph.services.cvm_registry import (
    find_cvm_code_in_df,
    get_cnpj_by_cvm_code,
    get_fallback_years,
    resolve_cvm_code,
)


class TestCVMRegistry:
    """Tests for the CVM Registry service."""

    @pytest.fixture
    def sample_cadastral_df(self):
        """Fixture providing a sample cadastral DataFrame for testing."""

        return pd.DataFrame(
            {
                "DENOM_SOCIAL": [
                    "WEG EQUIPAMENTOS ELÉTRICOS S.A.",
                    "WEG S.A.",
                    "PETROLEO BRASILEIRO S.A. PETROBRAS",
                    "VALE S.A.",
                ],
                "CD_CVM": ["005678", "001234", "009512", "004170"],
                "CNPJ_CIA": [
                    "00.000.000/0001-00",
                    "11.111.111/0001-11",
                    "22.222.222/0001-22",
                    "33.333.333/0001-33",
                ],
            }
        )

    def test_get_fallback_years(self):
        """Tests if fallback years are generated correctly."""

        # Action: Generate fallback years.
        years = get_fallback_years(3)

        # Assert: Verify the count, type, and descending order of the years.
        assert len(years) == 3
        assert all(isinstance(year, int) for year in years)
        assert years[0] >= years[1]

    def test_find_cvm_code_in_df_heuristic(self, sample_cadastral_df):
        """Tests if CVM code finding heuristic works correctly."""

        # Action & Assert: Verify that the heuristic correctly identifies the CVM code based on name length.
        assert find_cvm_code_in_df(sample_cadastral_df, "WEG") == "001234"

    def test_find_cvm_code_in_df_empty_df(self):
        """Tests if finding CVM code in an empty DataFrame returns None."""

        # Setup: Create an empty DataFrame.
        df_empty = pd.DataFrame(columns=["DENOM_SOCIAL", "CD_CVM"])

        # Action & Assert: Verify that searching in an empty DataFrame returns None.
        assert find_cvm_code_in_df(df_empty, "WEG") is None

    def test_find_cvm_code_in_df_no_match(self, sample_cadastral_df):
        """Tests if CVM code finding returns None when no match is found."""

        # Action & Assert: Verify that None is returned when no company name matches.
        assert find_cvm_code_in_df(sample_cadastral_df, "NON_EXISTENT_COMPANY") is None

    def test_get_cnpj_by_cvm_code_padding(self, sample_cadastral_df):
        """Tests if CNPJ retrieval by CVM code works with padding."""

        # Action & Assert: Verify that CNPJ retrieval works with both padded and unpadded CVM codes.
        assert get_cnpj_by_cvm_code(sample_cadastral_df, "1234") == "11.111.111/0001-11"
        assert get_cnpj_by_cvm_code(sample_cadastral_df, "abc") is None

    def test_get_cnpj_by_cvm_code_not_found(self, sample_cadastral_df):
        """Tests if CNPJ retrieval returns None when CVM code is not in DF."""

        # Action & Assert: Verify that invalid CVM codes or types return None.
        assert get_cnpj_by_cvm_code(sample_cadastral_df, "999999") is None
        assert get_cnpj_by_cvm_code(sample_cadastral_df, None) is None
        assert get_cnpj_by_cvm_code(sample_cadastral_df, []) is None

    def test_resolve_cvm_code_full_flow(self, mocker, sample_cadastral_df):
        """Tests the full flow of CVM code resolution."""

        # Setup: Mock ticker resolution, name normalization, and CVM code lookup.
        mock_resolve_ticker = mocker.patch(
            "nexus_equitygraph.services.cvm_registry.resolve_name_from_ticker"
        )
        mock_norm = mocker.patch(
            "nexus_equitygraph.services.cvm_registry.normalize_company_name"
        )

        mock_resolve_ticker.return_value = "VALE"
        mock_norm.return_value = "VALE"

        mock_find = mocker.patch(
            "nexus_equitygraph.services.cvm_registry.find_cvm_code_in_df"
        )
        mock_find.side_effect = [None, "4170"]

        # Action: Resolve the CVM code for a ticker.
        res = resolve_cvm_code(sample_cadastral_df, "VALE3")

        # Assert: Verify the resolved code and the sequence of lookup attempts.
        assert res == "4170"
        assert mock_find.call_count == 2

    def test_resolve_cvm_code_normalization_fallback(self, sample_cadastral_df):
        """Tests if CVM code resolution works with name normalization fallback."""

        # Action: Resolve a CVM code using a name that requires normalization.
        res = resolve_cvm_code(sample_cadastral_df, "WEG S.A.")

        # Assert: Verify that the code is found after normalization.
        assert res == "001234"

    def test_resolve_cvm_code_no_match_at_all(self, mocker, sample_cadastral_df):
        """Tests if resolve_cvm_code returns None when all strategies fail."""

        # Setup: Mock the ticker resolver to fail.
        mocker.patch(
            "nexus_equitygraph.services.cvm_registry.resolve_name_from_ticker",
            return_value=None,
        )

        # Action & Assert: Verify that None is returned when all resolution strategies fail.
        assert resolve_cvm_code(sample_cadastral_df, "EMPRESA_INEXISTENTE_XYZ") is None
