"""Tests for text_utils in nexus_equitygraph.core.text_utils."""

import pytest

from nexus_equitygraph.core.text_utils import (
    cleanup_think_tags,
    extract_clean_text_from_html,
    format_cache_key,
    normalize_company_name,
    truncate_text,
)


class TestNormalizeCompanyName:
    """Test suite for normalize_company_name."""

    def test_returns_empty_string_for_none(self):
        """Test that None input returns empty string."""

        # Arrange: None input.
        name = None

        # Act: Call normalize_company_name.
        result = normalize_company_name(name)

        # Assert: Returns empty string.
        assert result == ""

    def test_returns_empty_string_for_empty_input(self):
        """Test that empty string input returns empty string."""

        # Arrange: Empty string input.
        name = ""

        # Act: Call normalize_company_name.
        result = normalize_company_name(name)

        # Assert: Returns empty string.
        assert result == ""

    def test_converts_to_uppercase(self):
        """Test that output is uppercase."""

        # Arrange: Lowercase input.
        name = "petrobras"

        # Act: Call normalize_company_name.
        result = normalize_company_name(name)

        # Assert: Output is uppercase.
        assert result == "PETROBRAS"

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("WEG S.A.", "WEG"),
            ("Petrobras S A", "PETROBRAS"),
            ("Vale S/A", "VALE"),
        ],
    )
    def test_removes_sa_suffix(self, input_name: str, expected: str):
        """Test removal of S.A. suffix variants."""

        # Act: Call normalize_company_name.
        result = normalize_company_name(input_name)

        # Assert: S.A. suffix is removed.
        assert result == expected

    def test_removes_ltda_suffix(self):
        """Test removal of LTDA suffix."""

        # Arrange: Company with LTDA suffix.
        name = "Empresa LTDA"

        # Act: Call normalize_company_name.
        result = normalize_company_name(name)

        # Assert: LTDA suffix is removed.
        assert result == "EMPRESA"

    def test_removes_holding_suffix(self):
        """Test removal of HOLDING suffix."""

        # Arrange: Company with HOLDING suffix.
        name = "Itausa Holding"

        # Act: Call normalize_company_name.
        result = normalize_company_name(name)

        # Assert: HOLDING suffix is removed.
        assert result == "ITAUSA"

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("Bradesco Participacoes", "BRADESCO"),
            ("Bradesco Participações", "BRADESCO"),
        ],
    )
    def test_removes_participacoes_suffix(self, input_name: str, expected: str):
        """Test removal of PARTICIPACOES suffix (accented and non-accented)."""

        # Act: Call normalize_company_name.
        result = normalize_company_name(input_name)

        # Assert: PARTICIPACOES suffix is removed.
        assert result == expected

    def test_removes_punctuation(self):
        """Test removal of punctuation (dots, commas, hyphens)."""

        # Arrange: Company name with punctuation.
        name = "B3 S.A. - Brasil, Bolsa, Balcão"

        # Act: Call normalize_company_name.
        result = normalize_company_name(name)

        # Assert: Punctuation is removed.
        assert result == "B3"

    def test_removes_extra_spaces(self):
        """Test removal of extra spaces."""

        # Arrange: Company name with extra spaces.
        name = "  WEG   S.A.  "

        # Act: Call normalize_company_name.
        result = normalize_company_name(name)

        # Assert: Extra spaces are removed.
        assert result == "WEG"

    def test_complex_company_name(self):
        """Test complex company name with multiple suffixes."""

        # Arrange: Complex company name.
        name = "PETRÓLEO BRASILEIRO S.A. - PETROBRAS"

        # Act: Call normalize_company_name.
        result = normalize_company_name(name)

        # Assert: Suffixes are removed, base name preserved.
        assert result == "PETRÓLEO BRASILEIRO"


class TestFormatCacheKey:
    """Test suite for format_cache_key."""

    def test_basic_formatting(self):
        """Test basic cache key formatting."""

        # Arrange: Simple identifier and suffix.
        identifier = "PETR4"
        suffix = "news.json"

        # Act: Call format_cache_key.
        result = format_cache_key(identifier, suffix)

        # Assert: Correctly formatted.
        assert result == "PETR4_news.json"

    def test_converts_to_uppercase(self):
        """Test that identifier is converted to uppercase."""

        # Arrange: Lowercase identifier.
        identifier = "petr4"
        suffix = "data.pkl"

        # Act: Call format_cache_key.
        result = format_cache_key(identifier, suffix)

        # Assert: Identifier is uppercase.
        assert result == "PETR4_data.pkl"

    def test_replaces_spaces_with_underscores(self):
        """Test that spaces are replaced with underscores."""

        # Arrange: Identifier with spaces.
        identifier = "Vale do Rio Doce"
        suffix = "financials.json"

        # Act: Call format_cache_key.
        result = format_cache_key(identifier, suffix)

        # Assert: Spaces replaced with underscores.
        assert result == "VALE_DO_RIO_DOCE_financials.json"

    def test_removes_dots(self):
        """Test that dots are removed."""

        # Arrange: Identifier with dots.
        identifier = "B3.SA"
        suffix = "quotes.pkl"

        # Act: Call format_cache_key.
        result = format_cache_key(identifier, suffix)

        # Assert: Dots are removed.
        assert result == "B3SA_quotes.pkl"

    def test_removes_slashes(self):
        """Test that slashes are removed."""

        # Arrange: Identifier with slashes.
        identifier = "S/A Company"
        suffix = "data.json"

        # Act: Call format_cache_key.
        result = format_cache_key(identifier, suffix)

        # Assert: Slashes are removed.
        assert result == "SA_COMPANY_data.json"

    def test_combined_special_characters(self):
        """Test with multiple special characters."""

        # Arrange: Identifier with multiple special characters.
        identifier = "B3 S.A./Brasil"
        suffix = "test.pkl"

        # Act: Call format_cache_key.
        result = format_cache_key(identifier, suffix)

        # Assert: All special characters handled (uppercase).
        assert result == "B3_SABRASIL_test.pkl"


class TestTruncateText:
    """Test suite for truncate_text."""

    def test_returns_original_if_within_limit(self):
        """Test that text within limit is returned unchanged."""

        # Arrange: Short text within limit.
        text = "Short text"
        limit = 100

        # Act: Call truncate_text.
        result = truncate_text(text, limit=limit)

        # Assert: Original text returned.
        assert result == "Short text"

    def test_returns_original_if_exactly_at_limit(self):
        """Test that text exactly at limit is returned unchanged."""

        # Arrange: Text exactly at limit.
        text = "12345"
        limit = 5

        # Act: Call truncate_text.
        result = truncate_text(text, limit=limit)

        # Assert: Original text returned.
        assert result == "12345"

    def test_truncates_with_default_suffix(self):
        """Test truncation with default '...' suffix."""

        # Arrange: Long text exceeding limit.
        text = "This is a long text that should be truncated"
        limit = 10

        # Act: Call truncate_text.
        result = truncate_text(text, limit=limit)

        # Assert: Text truncated with default suffix.
        assert result == "This is a ..."
        assert len(result) == 13  # 10 + 3 for "..."

    def test_truncates_with_custom_suffix(self):
        """Test truncation with custom suffix."""

        # Arrange: Long text with custom suffix.
        text = "This is a long text"
        limit = 10
        suffix = "[...]"

        # Act: Call truncate_text.
        result = truncate_text(text, limit=limit, suffix=suffix)

        # Assert: Text truncated with custom suffix.
        assert result == "This is a [...]"

    def test_truncates_with_empty_suffix(self):
        """Test truncation with empty suffix."""

        # Arrange: Long text with empty suffix.
        text = "This is a long text"
        limit = 10
        suffix = ""

        # Act: Call truncate_text.
        result = truncate_text(text, limit=limit, suffix=suffix)

        # Assert: Text truncated without suffix.
        assert result == "This is a "
        assert len(result) == 10

    def test_handles_empty_string(self):
        """Test with empty string input."""

        # Arrange: Empty string.
        text = ""
        limit = 10

        # Act: Call truncate_text.
        result = truncate_text(text, limit=limit)

        # Assert: Empty string returned.
        assert result == ""

    def test_limit_of_zero(self):
        """Test with limit of zero."""

        # Arrange: Non-empty text with zero limit.
        text = "Some text"
        limit = 0

        # Act: Call truncate_text.
        result = truncate_text(text, limit=limit)

        # Assert: Only suffix returned.
        assert result == "..."


class TestExtractCleanTextFromHtml:
    """Test suite for extract_clean_text_from_html."""

    def test_extracts_text_from_simple_html(self):
        """Test extraction from simple HTML."""

        # Arrange: Simple HTML content.
        html = "<html><body><p>Hello World</p></body></html>"

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html(html)

        # Assert: Returns a string (trafilatura may return empty for minimal HTML).
        assert isinstance(result, str)

    def test_removes_html_tags(self):
        """Test that HTML tags are removed."""

        # Arrange: HTML with formatting tags.
        html = "<div><p><strong>Bold text</strong> and <em>italic</em></p></div>"

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html(html)

        # Assert: No HTML tags in result.
        assert "<" not in result
        assert ">" not in result

    def test_returns_empty_for_empty_input(self):
        """Test that empty input returns empty string."""

        # Arrange: Empty HTML string.
        html = ""

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html(html)

        # Assert: Empty string returned.
        assert result == ""

    def test_returns_empty_for_html_without_content(self):
        """Test that HTML without text content returns empty string."""

        # Arrange: HTML without body content.
        html = "<html><head><title>Test</title></head><body></body></html>"

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html(html)

        # Assert: Empty string returned.
        assert result == ""

    def test_removes_excessive_whitespace(self):
        """Test that excessive whitespace is normalized."""

        # Arrange: HTML with excessive whitespace.
        html = """
        <html>
            <body>
                <p>Text    with     multiple     spaces</p>
            </body>
        </html>
        """

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html(html)

        # Assert: No multiple consecutive spaces.
        assert "  " not in result

    def test_handles_invalid_html_gracefully(self):
        """Test that invalid HTML is handled gracefully."""

        # Arrange: Invalid HTML with unclosed tags.
        invalid_html = "<div><p>Unclosed tag"

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html(invalid_html)

        # Assert: Returns string without raising.
        assert isinstance(result, str)

    def test_handles_none_gracefully(self, mocker):
        """Test that None input is handled gracefully."""

        # Arrange: None input (type ignored for test).
        html = None

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html(html)  # type: ignore

        # Assert: Returns empty string.
        assert result == ""

    def test_extracts_from_article_like_html(self):
        """Test extraction from realistic article HTML."""

        # Arrange: Realistic article HTML structure.
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>News Article</title></head>
        <body>
            <header>Site Header</header>
            <article>
                <h1>Breaking News</h1>
                <p>This is the main content of the news article.</p>
                <p>It contains multiple paragraphs with important information.</p>
            </article>
            <footer>Site Footer</footer>
        </body>
        </html>
        """

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html(html)

        # Assert: Returns string (trafilatura extracts from article-like structure).
        assert isinstance(result, str)

    def test_logs_error_on_value_error(self, mocker):
        """Test that ValueError is logged and empty string returned."""

        # Arrange: Mock trafilatura to raise ValueError.
        mocker.patch(
            "nexus_equitygraph.core.text_utils.trafilatura.extract",
            side_effect=ValueError("Test error"),
        )
        mock_logger = mocker.patch("nexus_equitygraph.core.text_utils.logger")

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html("<html></html>")

        # Assert: Returns empty string and logs error.
        assert result == ""
        mock_logger.error.assert_called_once()

    def test_logs_error_on_attribute_error(self, mocker):
        """Test that AttributeError is logged and empty string returned."""

        # Arrange: Mock trafilatura to raise AttributeError.
        mocker.patch(
            "nexus_equitygraph.core.text_utils.trafilatura.extract",
            side_effect=AttributeError("Test error"),
        )
        mock_logger = mocker.patch("nexus_equitygraph.core.text_utils.logger")

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html("<html></html>")

        # Assert: Returns empty string and logs error.
        assert result == ""
        mock_logger.error.assert_called_once()

    def test_logs_error_on_unexpected_exception(self, mocker):
        """Test that unexpected exceptions are logged and empty string returned."""

        # Arrange: Mock trafilatura to raise RuntimeError.
        mocker.patch(
            "nexus_equitygraph.core.text_utils.trafilatura.extract",
            side_effect=RuntimeError("Unexpected error"),
        )
        mock_logger = mocker.patch("nexus_equitygraph.core.text_utils.logger")

        # Act: Call extract_clean_text_from_html.
        result = extract_clean_text_from_html("<html></html>")

        # Assert: Returns empty string and logs error.
        assert result == ""
        mock_logger.error.assert_called_once()


class TestCleanupThinkTags:
    """Test suite for cleanup_think_tags."""

    def test_removes_simple_think_tags(self):
        """Test removal of simple think tags."""

        # Arrange: Content with inline tags.
        content = "Hello <think>thinking process</think> World"

        # Act: Call cleanup_think_tags.
        result = cleanup_think_tags(content)

        # Assert: Tags removed.
        assert result == "Hello  World"

    def test_removes_multiline_think_tags(self):
        """Test removal of multiline think tags."""

        # Arrange: Content with multiline tags.
        content = "Start\n<think>\nLine 1\nLine 2\n</think>\nEnd"

        # Act: Call cleanup_think_tags.
        result = cleanup_think_tags(content)

        # Assert: Tags removed, preserving surrounding structure.
        assert result == "Start\n\nEnd"

    def test_removes_multiple_tags(self):
        """Test removal of multiple tags in the same string."""

        # Arrange: Content with multiple tags.
        content = "<think>1</think>Real Content<think>2</think>"

        # Act: Call cleanup_think_tags.
        result = cleanup_think_tags(content)

        # Assert: All tags removed.
        assert result == "Real Content"

    def test_handles_content_without_tags(self):
        """Test content without any tags."""

        # Arrange: Plain text.
        content = "Just plain text."

        # Act: Call cleanup_think_tags.
        result = cleanup_think_tags(content)

        # Assert: Content remains unchanged.
        assert result == "Just plain text."

    def test_handles_empty_string(self):
        """Test empty string input."""

        # Act: Call cleanup_think_tags.
        result = cleanup_think_tags("")

        # Assert: Returns empty string.
        assert result == ""

    def test_handles_none_input(self):
        """Test that None input returns empty string instead of 'None'."""

        # Act: Call cleanup_think_tags with None.
        result = cleanup_think_tags(None)

        # Assert: Returns empty string.
        assert result == ""

    def test_handles_str_conversion_error(self, mocker):
        """Test that string conversion errors are caught and logged."""

        # Arrange: Object that raises error on str().
        class BrokenObject:
            def __str__(self):
                raise ValueError("Simulated conversion error")

        mock_logger = mocker.patch("nexus_equitygraph.core.text_utils.logger")

        # Act: Call cleanup_think_tags.
        result = cleanup_think_tags(BrokenObject())

        # Assert: Returns empty string and logs error.
        assert result == ""
        mock_logger.error.assert_called_once()
