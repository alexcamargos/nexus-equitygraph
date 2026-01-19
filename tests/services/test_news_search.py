"""Tests for news_search in nexus_equitygraph.services.news_search."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pytest
import requests

from nexus_equitygraph.domain.state import NewsArticle
from nexus_equitygraph.services.news_search import (
    ALLOWLIST_DOMAINS,
    fetch_url_content,
    filter_recent_articles,
    scrape_article_urls,
    search_news_ddgs,
)

VALID_ARTICLE_TEXT = "A" * 150  # Text > 100 chars to pass validation.


@pytest.fixture
def mock_http_client(mocker):
    """Creates a mock HTTP client with successful response."""

    client = mocker.MagicMock()
    response = mocker.MagicMock()
    response.status_code = 200
    response.text = "<html><body><p>Content</p></body></html>"
    client.get.return_value = response

    return client, response


@pytest.fixture
def mock_ddgs(mocker):
    """Creates a mock DDGS context manager."""

    instance = mocker.MagicMock()
    mock = mocker.patch("nexus_equitygraph.services.news_search.DDGS")
    mock.return_value.__enter__.return_value = instance

    return instance


@pytest.fixture
def sample_news_article():
    """Creates a sample NewsArticle for testing."""

    return NewsArticle(
        title="Test Article",
        url="https://example.com",
        text=VALID_ARTICLE_TEXT,
        timestamp="2025-01-15T10:00:00Z",
    )


class TestAllowlistDomains:
    """Test suite for ALLOWLIST_DOMAINS constant."""

    @pytest.mark.parametrize(
        "domain",
        [
            # Major financial sources.
            "reuters.com",
            "bloomberg.com",
            "valor.globo.com",
            "infomoney.com.br",
            # Brazilian sources.
            "folha.uol.com.br",
            "estadao.com.br",
            "exame.com",
            "suno.com.br",
        ],
    )
    def test_contains_expected_domains(self, domain: str):
        """Tests that allowlist contains expected news domains."""

        # Assert: Domain is in allowlist.
        assert domain in ALLOWLIST_DOMAINS

    def test_is_non_empty_list(self):
        """Tests that allowlist is a non-empty list."""

        # Assert: Is a list with items.
        assert isinstance(ALLOWLIST_DOMAINS, list)
        assert len(ALLOWLIST_DOMAINS) > 0


class TestFetchUrlContent:
    """Test suite for fetch_url_content function."""

    def test_returns_news_article_on_success(self, mock_http_client, mocker):
        """Tests successful fetch returns NewsArticle."""

        # Arrange: Mock HTTP client and response.
        mock_client, mock_response = mock_http_client
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Content</p></body></html>"
        mock_client.get.return_value = mock_response

        # Text must be > 100 chars to pass validation.
        long_text = "A" * 150
        mocker.patch(
            "nexus_equitygraph.services.news_search.extract_clean_text_from_html",
            return_value=long_text,
        )

        # Act: Fetch URL content.
        result = fetch_url_content(mock_client, "https://example.com/article", "Test Title")

        # Assert: Returns NewsArticle with correct data.
        assert result is not None
        assert isinstance(result, NewsArticle)
        assert result.title == "Test Title"
        assert result.url == "https://example.com/article"
        assert len(result.text) > 100

    def test_returns_none_on_non_200_status(self, mocker):
        """Tests that non-200 status code returns None."""

        # Arrange: Mock HTTP client with 404 response.
        mock_client = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        mock_logger = mocker.patch("nexus_equitygraph.services.news_search.logger")

        # Act: Fetch URL content.
        result = fetch_url_content(mock_client, "https://example.com/missing", "Missing Article")

        # Assert: Returns None and logs warning.
        assert result is None
        mock_logger.warning.assert_called_once()

    @pytest.mark.parametrize(
        "extracted_text",
        [
            pytest.param("", id="empty_text"),
            pytest.param("Short", id="short_text"),
            pytest.param("A" * 99, id="just_under_100_chars"),
        ],
    )
    def test_returns_none_on_insufficient_text(self, mocker, mock_http_client, extracted_text: str):
        """Tests that insufficient extracted text returns None."""

        # Arrange: Mock extraction to return insufficient text.
        mock_client, _ = mock_http_client
        mocker.patch(
            "nexus_equitygraph.services.news_search.extract_clean_text_from_html",
            return_value=extracted_text,
        )

        # Act: Fetch URL content.
        result = fetch_url_content(mock_client, "https://example.com/short", "Short Article")

        # Assert: Returns None (text <= 100 chars).
        assert result is None

    def test_returns_none_on_request_exception(self, mocker):
        """Tests that request exceptions return None."""

        # Arrange: Mock HTTP client that raises exception.
        mock_client = mocker.MagicMock()
        mock_client.get.side_effect = requests.exceptions.RequestException("Connection error")
        mock_logger = mocker.patch("nexus_equitygraph.services.news_search.logger")

        # Act: Fetch URL content.
        result = fetch_url_content(mock_client, "https://example.com/error", "Error Article")

        # Assert: Returns None and logs error.
        assert result is None
        mock_logger.error.assert_called_once()

    def test_timestamp_is_iso_format(self, mocker, mock_http_client):
        """Tests that returned article has ISO format timestamp."""

        # Arrange: Use mock HTTP client fixture.
        mock_client, _ = mock_http_client
        mocker.patch(
            "nexus_equitygraph.services.news_search.extract_clean_text_from_html",
            return_value=VALID_ARTICLE_TEXT,
        )

        # Act: Fetch URL content.
        result = fetch_url_content(mock_client, "https://example.com", "Title")

        # Assert: Timestamp is valid ISO format.
        assert result is not None
        # Should not raise ValueError
        datetime.fromisoformat(result.timestamp)


class TestFilterRecentArticles:
    """Test suite for filter_recent_articles function."""

    def test_filters_old_articles(self):
        """Tests that articles older than cutoff are filtered out."""

        # Arrange: Articles with different dates.
        now = datetime.now(timezone.utc)
        articles = [
            {"title": "Old", "date": (now - timedelta(days=60)).isoformat()},
            {"title": "Recent", "date": (now - timedelta(days=10)).isoformat()},
        ]

        # Act: Filter with 30-day window.
        result = filter_recent_articles(articles, days=30)

        # Assert: Only recent article remains.
        assert len(result) == 1
        assert result[0]["title"] == "Recent"

    def test_keeps_articles_within_window(self):
        """Tests that articles within window are kept."""

        # Arrange: All articles within window.
        now = datetime.now(timezone.utc)
        articles = [
            {"title": "Article 1", "date": (now - timedelta(days=5)).isoformat()},
            {"title": "Article 2", "date": (now - timedelta(days=15)).isoformat()},
            {"title": "Article 3", "date": (now - timedelta(days=25)).isoformat()},
        ]

        # Act: Filter with 30-day window.
        result = filter_recent_articles(articles, days=30)

        # Assert: All articles kept.
        assert len(result) == 3

    def test_uses_cached_at_field(self):
        """Tests that cached_at field is used when date is missing."""

        # Arrange: Article with cached_at instead of date.
        now = datetime.now(timezone.utc)
        articles = [
            {"title": "Cached", "cached_at": (now - timedelta(days=5)).isoformat()},
        ]

        # Act: Filter articles.
        result = filter_recent_articles(articles, days=30)

        # Assert: Article is kept.
        assert len(result) == 1
        assert result[0]["title"] == "Cached"

    @pytest.mark.parametrize(
        "articles",
        [
            pytest.param([{"title": "No Date"}], id="missing_date_field"),
            pytest.param([{"title": "Invalid", "date": "not-a-date"}], id="invalid_date_format"),
            pytest.param([], id="empty_list"),
        ],
    )
    def test_returns_empty_for_invalid_or_missing_dates(self, articles: List[Dict]):
        """Tests that articles with invalid/missing dates return empty list."""

        # Act: Filter articles.
        result = filter_recent_articles(articles, days=30)

        # Assert: No articles returned.
        assert result == []

    def test_default_days_is_30(self):
        """Tests that default window is 30 days."""

        # Arrange: Article at 31 days old.
        now = datetime.now(timezone.utc)
        articles = [
            {"title": "31 days", "date": (now - timedelta(days=31)).isoformat()},
            {"title": "29 days", "date": (now - timedelta(days=29)).isoformat()},
        ]

        # Act: Filter with default days.
        result = filter_recent_articles(articles)

        # Assert: Only 29-day article kept.
        assert len(result) == 1
        assert result[0]["title"] == "29 days"

    def test_handles_naive_datetime(self):
        """Tests that naive datetimes are treated as UTC."""

        # Arrange: Article with naive datetime (no timezone).
        now = datetime.now(timezone.utc)
        naive_date = (now - timedelta(days=5)).replace(tzinfo=None).isoformat()
        articles = [
            {"title": "Naive", "date": naive_date},
        ]

        # Act: Filter articles.
        result = filter_recent_articles(articles, days=30)

        # Assert: Article is kept.
        assert len(result) == 1


class TestSearchNewsDdgs:
    """Test suite for search_news_ddgs function."""

    def test_returns_candidates_from_allowlist(self, mock_ddgs):
        """Tests that results from allowlist domains are returned."""

        # Arrange: Configure mock DDGS with allowlist URL.
        mock_ddgs.news.return_value = [
            {
                "url": "https://reuters.com/article",
                "title": "Reuters Article",
                "date": "2025-01-15",
                "source": "Reuters",
            },
        ]

        # Act: Search news.
        result = search_news_ddgs("PETR4", set())

        # Assert: Reuters article is in candidates.
        assert len(result) == 1
        assert result[0]["url"] == "https://reuters.com/article"

    def test_filters_known_urls(self, mock_ddgs):
        """Tests that known URLs are filtered out."""

        # Arrange: Configure mock DDGS with known URL.
        mock_ddgs.news.return_value = [
            {"url": "https://reuters.com/known", "title": "Known", "date": "2025-01-15", "source": "Reuters"},
            {"url": "https://reuters.com/new", "title": "New", "date": "2025-01-15", "source": "Reuters"},
        ]
        known_urls = {"https://reuters.com/known"}

        # Act: Search news with known URLs.
        result = search_news_ddgs("PETR4", known_urls)

        # Assert: Only new URL is returned.
        assert len(result) == 1
        assert result[0]["url"] == "https://reuters.com/new"

    def test_filters_non_allowlist_domains(self, mock_ddgs):
        """Tests that non-allowlist domains are filtered out."""

        # Arrange: Configure mock DDGS with non-allowlist URL.
        mock_ddgs.news.return_value = [
            {"url": "https://random-blog.com/article", "title": "Blog", "date": "2025-01-15", "source": "Blog"},
        ]

        # Act: Search news.
        result = search_news_ddgs("PETR4", set(), recent_count=5)

        # Assert: No candidates (not in allowlist and has recent articles).
        assert len(result) == 0

    def test_fallback_when_few_candidates(self, mock_ddgs):
        """Tests fallback to non-allowlist when few candidates and no recent."""

        # Arrange: Configure mock DDGS with only non-allowlist URLs.
        mock_ddgs.news.return_value = [
            {"url": "https://random-blog.com/article", "title": "Blog", "date": "2025-01-15", "source": "Blog"},
        ]

        # Act: Search news with no recent articles.
        result = search_news_ddgs("PETR4", set(), recent_count=0)

        # Assert: Fallback includes non-allowlist URL.
        assert len(result) == 1
        assert result[0]["url"] == "https://random-blog.com/article"

    def test_uses_link_field_as_fallback(self, mock_ddgs):
        """Tests that 'link' field is used when 'url' is missing."""

        # Arrange: Configure mock DDGS with 'link' instead of 'url'.
        mock_ddgs.news.return_value = [
            {"link": "https://reuters.com/article", "title": "Article", "date": "2025-01-15", "source": "Reuters"},
        ]

        # Act: Search news.
        result = search_news_ddgs("PETR4", set())

        # Assert: Article is found using 'link' field.
        assert len(result) == 1
        assert result[0]["url"] == "https://reuters.com/article"

    def test_returns_empty_on_no_results(self, mock_ddgs):
        """Tests that empty list is returned when no results."""

        # Arrange: Configure mock DDGS with no results.
        mock_ddgs.news.return_value = []

        # Act: Search news.
        result = search_news_ddgs("unknown query", set())

        # Assert: Empty list returned.
        assert result == []


class TestScrapeArticleUrls:
    """Test suite for scrape_article_urls function."""

    def test_returns_empty_for_empty_candidates(self):
        """Tests that empty candidates returns empty list."""

        # Arrange: Empty candidates list.
        candidates: List[Dict] = []

        # Act: Scrape articles.
        result = scrape_article_urls(candidates, limit=5)

        # Assert: Empty list returned.
        assert result == []

    def test_scrapes_articles_successfully(self, mocker, sample_news_article):
        """Tests successful scraping of articles."""

        # Arrange: Mock fetch_url_content and http_client.
        mocker.patch(
            "nexus_equitygraph.services.news_search.fetch_url_content",
            return_value=sample_news_article,
        )
        mocker.patch("nexus_equitygraph.services.news_search.get_http_client")
        candidates = [
            {"url": "https://example.com", "title": "Test Article", "source": "Example"},
        ]

        # Act: Scrape articles.
        result = scrape_article_urls(candidates, limit=5)

        # Assert: Article is scraped and includes source.
        assert len(result) == 1
        assert result[0]["title"] == "Test Article"
        assert result[0]["source"] == "Example"
        assert "cached_at" in result[0]

    def test_respects_limit(self, mocker):
        """Tests that scraping stops at limit."""

        # Arrange: Mock fetch_url_content for multiple articles.
        def create_article(client, url, title):
            return NewsArticle(
                title=title,
                url=url,
                text=VALID_ARTICLE_TEXT,
                timestamp="2025-01-15T10:00:00Z",
            )

        mocker.patch(
            "nexus_equitygraph.services.news_search.fetch_url_content",
            side_effect=create_article,
        )
        mocker.patch("nexus_equitygraph.services.news_search.get_http_client")

        candidates = [
            {"url": f"https://example.com/{i}", "title": f"Article {i}", "source": "Example"} for i in range(10)
        ]

        # Act: Scrape with limit of 3.
        result = scrape_article_urls(candidates, limit=3)

        # Assert: Only 3 articles returned.
        assert len(result) == 3

    def test_skips_failed_fetches(self, mocker):
        """Tests that failed fetches are skipped."""

        # Arrange: Mock fetch_url_content to return None for some.
        call_count = [0]

        def mock_fetch(client, url, title):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                return None
            return NewsArticle(
                title=title,
                url=url,
                text=VALID_ARTICLE_TEXT,
                timestamp="2025-01-15T10:00:00Z",
            )

        mocker.patch(
            "nexus_equitygraph.services.news_search.fetch_url_content",
            side_effect=mock_fetch,
        )
        mocker.patch("nexus_equitygraph.services.news_search.get_http_client")

        candidates = [
            {"url": f"https://example.com/{i}", "title": f"Article {i}", "source": "Example"} for i in range(4)
        ]

        # Act: Scrape articles.
        result = scrape_article_urls(candidates, limit=10)

        # Assert: Only successful fetches are returned.
        assert len(result) == 2

    def test_adds_cached_at_timestamp(self, mocker, sample_news_article):
        """Tests that cached_at timestamp is added to articles."""

        # Arrange: Mock fetch_url_content with sample article.
        mocker.patch(
            "nexus_equitygraph.services.news_search.fetch_url_content",
            return_value=sample_news_article,
        )
        mocker.patch("nexus_equitygraph.services.news_search.get_http_client")
        candidates = [{"url": "https://example.com", "title": "Test", "source": "Example"}]

        # Act: Scrape articles.
        result = scrape_article_urls(candidates, limit=5)

        # Assert: cached_at is present and valid ISO format.
        assert "cached_at" in result[0]
        # Should not raise ValueError
        datetime.fromisoformat(result[0]["cached_at"])

    def test_uses_get_http_client(self, mocker):
        """Tests that get_http_client is called."""

        # Arrange: Mock dependencies.
        mock_get_client = mocker.patch("nexus_equitygraph.services.news_search.get_http_client")
        mocker.patch(
            "nexus_equitygraph.services.news_search.fetch_url_content",
            return_value=None,
        )
        candidates = [{"url": "https://example.com", "title": "Test", "source": "Example"}]

        # Act: Scrape articles.
        scrape_article_urls(candidates, limit=5)

        # Assert: get_http_client was called.
        mock_get_client.assert_called_once()
