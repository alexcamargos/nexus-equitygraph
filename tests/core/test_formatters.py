"""Tests for formatters in nexus_equitygraph.core.formatters."""

from typing import Dict

import pytest

from nexus_equitygraph.core.formatters import (
    ArticleLike,
    format_articles_output,
    format_single_article,
    normalize_article,
)


class MockArticle:
    """Mock class implementing ArticleLike protocol."""

    def __init__(
        self,
        title: str = "Test Title",
        url: str = "https://example.com",
        text: str = "Test content",
        timestamp: str = "2025-01-15T10:00:00Z",
    ):
        self.title = title
        self.url = url
        self.text = text
        self.timestamp = timestamp


@pytest.fixture
def sample_article() -> MockArticle:
    """A standard MockArticle for testing."""
    return MockArticle()


@pytest.fixture
def sample_article_dict() -> Dict[str, str]:
    """A standard normalized article dict for testing."""
    return {
        "title": "Test Title",
        "url": "https://example.com",
        "text": "Test content",
        "timestamp": "2025-01-15T10:00:00Z",
    }


@pytest.fixture
def long_text() -> str:
    """A text longer than default truncation limit (2500)."""
    return "A" * 5000


class TestArticleLikeProtocol:
    """Test suite for ArticleLike protocol."""

    def test_mock_article_implements_protocol(self):
        """Tests that MockArticle implements ArticleLike protocol."""

        # Arrange: Create mock article.
        article = MockArticle()

        # Act: Check protocol compliance.
        is_article_like = isinstance(article, ArticleLike)

        # Assert: Implements protocol.
        assert is_article_like

    def test_dict_does_not_implement_protocol(self):
        """Tests that dict does not implement ArticleLike protocol."""

        # Arrange: Create dict with article data.
        article_dict = {
            "title": "Test",
            "url": "https://example.com",
            "text": "Content",
            "timestamp": "2025-01-15T10:00:00Z",
        }

        # Act: Check protocol compliance.
        is_article_like = isinstance(article_dict, ArticleLike)

        # Assert: Dict does not implement protocol.
        assert not is_article_like


class TestNormalizeArticle:
    """Test suite for normalize_article function."""

    def test_normalizes_article_like_object(self):
        """Tests normalization of ArticleLike object."""

        # Arrange: Create ArticleLike object.
        article = MockArticle(
            title="Breaking News",
            url="https://news.com/article",
            text="Article content here",
            timestamp="2025-01-15T10:00:00Z",
        )

        # Act: Normalize article.
        result = normalize_article(article)

        # Assert: Returns dict with correct values.
        assert result == {
            "title": "Breaking News",
            "url": "https://news.com/article",
            "text": "Article content here",
            "timestamp": "2025-01-15T10:00:00Z",
        }

    def test_normalizes_complete_dict(self):
        """Tests normalization of complete dictionary."""

        # Arrange: Create complete dict.
        article_dict = {
            "title": "Dict Title",
            "url": "https://dict.com",
            "text": "Dict content",
            "timestamp": "2025-01-15T12:00:00Z",
        }

        # Act: Normalize article.
        result = normalize_article(article_dict)

        # Assert: Returns dict with correct values.
        assert result == article_dict

    @pytest.mark.parametrize(
        "missing_field,expected_default",
        [
            ("title", "No Title"),
            ("url", ""),
            ("text", ""),
            ("timestamp", ""),
        ],
    )
    def test_normalizes_dict_with_missing_field(self, missing_field: str, expected_default: str):
        """Tests that missing fields default to expected values."""

        # Arrange: Complete dict, then remove the field being tested.
        article_dict = {
            "title": "Title",
            "url": "https://example.com",
            "text": "Content",
            "timestamp": "2025-01-15T10:00:00Z",
        }
        del article_dict[missing_field]

        # Act: Normalize article.
        result = normalize_article(article_dict)

        # Assert: Missing field defaults to expected value.
        assert result[missing_field] == expected_default

    def test_normalizes_empty_dict(self):
        """Tests normalization of empty dictionary."""

        # Arrange: Empty dict.
        article_dict: dict = {}

        # Act: Normalize article.
        result = normalize_article(article_dict)

        # Assert: All fields have defaults.
        assert result == {
            "title": "No Title",
            "url": "",
            "text": "",
            "timestamp": "",
        }


class TestFormatSingleArticle:
    """Test suite for format_single_article function."""

    def test_formats_article_to_markdown(self):
        """Tests that article is formatted as markdown."""

        # Arrange: Normalized article dict.
        article = {
            "title": "Test Article",
            "url": "https://example.com/article",
            "text": "This is the article content.",
            "timestamp": "2025-01-15T10:00:00Z",
        }

        # Act: Format article.
        result = format_single_article(article)

        # Assert: Contains markdown elements.
        assert "#### Test Article" in result
        assert "**Source:** https://example.com/article" in result
        assert "**Date:** 2025-01-15T10:00:00Z" in result
        assert "This is the article content." in result
        assert "---" in result

    def test_formats_article_with_empty_fields(self):
        """Tests formatting with empty field values."""

        # Arrange: Article with empty fields.
        article = {
            "title": "",
            "url": "",
            "text": "",
            "timestamp": "",
        }

        # Act: Format article.
        result = format_single_article(article)

        # Assert: Structure is maintained with empty values.
        assert "#### " in result
        assert "**Source:** " in result
        assert "**Date:** " in result
        assert "---" in result

    def test_output_is_joined_with_newlines(self):
        """Tests that output lines are joined with newlines."""

        # Arrange: Article dict.
        article = {
            "title": "Title",
            "url": "https://url.com",
            "text": "Content",
            "timestamp": "2025-01-15",
        }

        # Act: Format article.
        result = format_single_article(article)

        # Assert: Contains newlines between sections.
        lines = result.split("\n")
        assert len(lines) >= 5  # title, source, date, text, separator


class TestFormatArticlesOutput:
    """Test suite for format_articles_output function."""

    def test_formats_multiple_articles(self):
        """Tests formatting of multiple articles."""

        # Arrange: List of articles.
        articles = [
            MockArticle(title="Article 1", text="Content 1"),
            MockArticle(title="Article 2", text="Content 2"),
        ]

        # Act: Format articles.
        result = format_articles_output(articles)

        # Assert: Both articles are in output.
        assert "Article 1" in result
        assert "Article 2" in result
        assert "Content 1" in result
        assert "Content 2" in result

    def test_formats_with_header(self):
        """Tests that header is included when provided."""

        # Arrange: Articles and header.
        articles = [MockArticle()]
        header = "Latest News"

        # Act: Format with header.
        result = format_articles_output(articles, header=header)

        # Assert: Header is present with markdown formatting.
        assert "### Latest News" in result

    def test_formats_without_header(self):
        """Tests that no header is included when not provided."""

        # Arrange: Articles without header.
        articles = [MockArticle(title="Only Article")]

        # Act: Format without header.
        result = format_articles_output(articles)

        # Assert: No level-3 header (###), starts with level-4 article title (####).
        assert result.startswith("####")
        assert "#### Only Article" in result

    def test_formats_with_none_header(self):
        """Tests that None header is not included."""

        # Arrange: Articles with explicit None header.
        articles = [MockArticle()]

        # Act: Format with None header.
        result = format_articles_output(articles, header=None)

        # Assert: Starts with article title (####), not section header (### ).
        assert result.startswith("####")

    def test_truncates_text_when_snippet_true(self):
        """Tests that text is truncated when snippet=True."""

        # Arrange: Article with long text.
        long_text = "A" * 5000
        articles = [MockArticle(text=long_text)]

        # Act: Format with snippet.
        result = format_articles_output(articles, snippet=True, limit=100)

        # Assert: Text is truncated with suffix.
        assert "A" * 100 in result
        assert "..." in result
        assert "A" * 5000 not in result

    def test_does_not_truncate_when_snippet_false(self):
        """Tests that text is not truncated when snippet=False."""

        # Arrange: Article with long text.
        long_text = "B" * 5000
        articles = [MockArticle(text=long_text)]

        # Act: Format without snippet.
        result = format_articles_output(articles, snippet=False)

        # Assert: Full text is present.
        assert "B" * 5000 in result

    def test_formats_empty_list(self):
        """Tests formatting of empty article list."""

        # Arrange: Empty list.
        articles: list = []

        # Act: Format empty list.
        result = format_articles_output(articles)

        # Assert: Returns empty string (no header, no articles).
        assert result == ""

    def test_formats_empty_list_with_header(self):
        """Tests formatting of empty list with header."""

        # Arrange: Empty list with header.
        articles: list = []
        header = "No Results"

        # Act: Format with header.
        result = format_articles_output(articles, header=header)

        # Assert: Only header is present.
        assert result == "### No Results\n"

    def test_formats_dict_articles(self):
        """Tests formatting of dictionary articles."""

        # Arrange: List of dicts.
        articles = [
            {"title": "Dict Article", "url": "https://dict.com", "text": "Dict text", "timestamp": "2025-01-15"},
        ]

        # Act: Format dicts.
        result = format_articles_output(articles)

        # Assert: Dict is properly formatted.
        assert "Dict Article" in result
        assert "https://dict.com" in result

    def test_formats_mixed_articles(self):
        """Tests formatting of mixed ArticleLike and dict articles."""

        # Arrange: Mixed list.
        articles = [
            MockArticle(title="Object Article"),
            {"title": "Dict Article", "url": "", "text": "", "timestamp": ""},
        ]

        # Act: Format mixed list.
        result = format_articles_output(articles)

        # Assert: Both types are formatted.
        assert "Object Article" in result
        assert "Dict Article" in result

    def test_custom_limit_for_truncation(self):
        """Tests custom limit parameter for truncation."""

        # Arrange: Article with text longer than custom limit.
        text = "X" * 200
        articles = [MockArticle(text=text)]

        # Act: Format with custom limit.
        result = format_articles_output(articles, snippet=True, limit=50)

        # Assert: Text truncated at custom limit.
        assert "X" * 50 in result
        assert "X" * 51 not in result.replace("...", "")

    def test_default_limit_is_2500(self):
        """Tests that default limit is 2500 characters."""

        # Arrange: Article with text longer than default limit.
        text = "Y" * 3000
        articles = [MockArticle(text=text)]

        # Act: Format with snippet using default limit.
        result = format_articles_output(articles, snippet=True)

        # Assert: Text truncated at 2500.
        assert "Y" * 2500 in result
        assert "Y" * 2501 not in result.replace("...", "")
