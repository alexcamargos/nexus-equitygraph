"""Tests for news_tools in nexus_equitygraph.tools.news_tools."""

from typing import Any, Dict, List

import pytest
from ddgs.exceptions import DDGSException

from nexus_equitygraph.tools.news_tools import SEARCH_RESULT_LIMIT, fetch_news_articles


@pytest.fixture
def mock_cache_manager(mocker):
    """Creates a mock cache manager."""

    manager = mocker.MagicMock()
    mocker.patch(
        "nexus_equitygraph.tools.news_tools.get_json_cache_manager",
        return_value=manager,
    )

    return manager


@pytest.fixture
def sample_cached_articles() -> List[Dict[str, Any]]:
    """Creates sample cached articles for testing."""

    return [
        {
            "url": "https://example.com/article1",
            "title": "Article 1",
            "text": "A" * 150,
            "timestamp": "2025-01-15T10:00:00Z",
            "source": "Example",
            "cached_at": "2025-01-15T10:00:00Z",
        },
        {
            "url": "https://example.com/article2",
            "title": "Article 2",
            "text": "B" * 150,
            "timestamp": "2025-01-14T10:00:00Z",
            "source": "Example",
            "cached_at": "2025-01-14T10:00:00Z",
        },
    ]


@pytest.fixture
def sample_new_articles() -> List[Dict[str, Any]]:
    """Creates sample new articles from scraping."""

    return [
        {
            "url": "https://example.com/new1",
            "title": "New Article",
            "text": "C" * 150,
            "timestamp": "2025-01-16T10:00:00Z",
            "source": "News Source",
            "cached_at": "2025-01-16T10:00:00Z",
        },
    ]


class TestSearchResultLimit:
    """Test suite for SEARCH_RESULT_LIMIT constant."""

    def test_default_value(self):
        """Tests that SEARCH_RESULT_LIMIT has expected default value."""

        # Assert: Default limit is 5.
        assert SEARCH_RESULT_LIMIT == 5

    def test_is_integer(self):
        """Tests that SEARCH_RESULT_LIMIT is an integer."""

        # Assert: Is an integer.
        assert isinstance(SEARCH_RESULT_LIMIT, int)


class TestFetchNewsArticles:
    """Test suite for fetch_news_articles function."""

    def test_returns_formatted_output_with_new_articles(self, mocker, mock_cache_manager, sample_new_articles):
        """Tests successful fetch returns formatted output with new articles."""

        # Arrange: Mock dependencies.
        mock_cache_manager.load_cache.return_value = []
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[{"url": "https://example.com/new1", "title": "New Article"}],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=sample_new_articles,
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.format_articles_output",
            return_value="Formatted Output",
        )

        # Act: Fetch news articles.
        result = fetch_news_articles.invoke({"query": "PETR4"})

        # Assert: Returns formatted output.
        assert result == "Formatted Output"
        mock_cache_manager.save_cache.assert_called_once()

    def test_returns_cached_articles_when_no_new_found(self, mocker, mock_cache_manager, sample_cached_articles):
        """Tests that cached articles are returned when no new articles found."""

        # Arrange: Mock with cached articles but no new ones.
        mock_cache_manager.load_cache.return_value = sample_cached_articles
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=sample_cached_articles,
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.format_articles_output",
            return_value="Cached Articles",
        )

        # Act: Fetch news articles.
        result = fetch_news_articles.invoke({"query": "VALE3"})

        # Assert: Returns cached articles, no save called.
        assert result == "Cached Articles"
        mock_cache_manager.save_cache.assert_not_called()

    def test_returns_no_news_message_when_empty(self, mocker, mock_cache_manager):
        """Tests that appropriate message is returned when no news found."""

        # Arrange: Mock with no cached or new articles.
        mock_cache_manager.load_cache.return_value = []
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=[],
        )

        # Act: Fetch news articles.
        result = fetch_news_articles.invoke({"query": "UNKNOWN"})

        # Assert: Returns no news message.
        assert result == "Nenhuma notícia relevante encontrada nos últimos 30 dias."

    def test_returns_cached_on_ddgs_exception_with_history(self, mocker, mock_cache_manager, sample_cached_articles):
        """Tests fallback to cached articles on DDGS exception."""

        # Arrange: Mock DDGS to raise exception.
        mock_cache_manager.load_cache.return_value = sample_cached_articles
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=sample_cached_articles,
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            side_effect=DDGSException("Rate limited"),
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.format_articles_output",
            return_value="Histórico (Busca Falhou)",
        )

        # Act: Fetch news articles.
        result = fetch_news_articles.invoke({"query": "ITUB4"})

        # Assert: Returns cached with failure header.
        assert result == "Histórico (Busca Falhou)"

    def test_returns_error_on_ddgs_exception_without_history(self, mocker, mock_cache_manager):
        """Tests error message on DDGS exception when no history exists."""

        # Arrange: Mock DDGS to raise exception with no history.
        mock_cache_manager.load_cache.return_value = []
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            side_effect=DDGSException("Connection error"),
        )

        # Act: Fetch news articles.
        result = fetch_news_articles.invoke({"query": "BBDC4"})

        # Assert: Returns error message.
        assert "Erro na busca e sem histórico" in result
        assert "Connection error" in result

    def test_uses_custom_num_results(self, mocker, mock_cache_manager, sample_cached_articles):
        """Tests that custom num_results parameter is respected."""

        # Arrange: Create more articles than requested.
        many_articles = sample_cached_articles * 5  # 10 articles
        mock_cache_manager.load_cache.return_value = many_articles
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=many_articles,
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=[],
        )
        mock_format = mocker.patch(
            "nexus_equitygraph.tools.news_tools.format_articles_output",
            return_value="Formatted",
        )

        # Act: Fetch with custom num_results.
        fetch_news_articles.invoke({"query": "MGLU3", "num_results": 3})

        # Assert: format_articles_output called with limited articles.
        call_args = mock_format.call_args
        articles_passed = call_args[0][0]
        assert len(articles_passed) == 3

    def test_builds_known_urls_from_cache(self, mocker, mock_cache_manager, sample_cached_articles):
        """Tests that known URLs are correctly built from cached articles."""

        # Arrange: Mock dependencies.
        mock_cache_manager.load_cache.return_value = sample_cached_articles
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=sample_cached_articles,
        )
        mock_search = mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.format_articles_output",
            return_value="Formatted",
        )

        # Act: Fetch news articles.
        fetch_news_articles.invoke({"query": "WEGE3"})

        # Assert: search_news_ddgs called with correct known_urls.
        call_args = mock_search.call_args
        known_urls = call_args[0][1]
        assert "https://example.com/article1" in known_urls
        assert "https://example.com/article2" in known_urls

    def test_handles_non_list_cache_data(self, mocker, mock_cache_manager):
        """Tests that non-list cache data is handled gracefully."""

        # Arrange: Return dict instead of list (edge case).
        mock_cache_manager.load_cache.return_value = {"invalid": "data"}
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=[],
        )

        # Act: Fetch news articles.
        result = fetch_news_articles.invoke({"query": "RENT3"})

        # Assert: Returns no news message (gracefully handles invalid cache).
        assert result == "Nenhuma notícia relevante encontrada nos últimos 30 dias."

    def test_handles_none_cache_data(self, mocker, mock_cache_manager):
        """Tests that None cache data is handled gracefully."""

        # Arrange: Return None from cache.
        mock_cache_manager.load_cache.return_value = None
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=[],
        )

        # Act: Fetch news articles.
        result = fetch_news_articles.invoke({"query": "EGIE3"})

        # Assert: Returns no news message.
        assert result == "Nenhuma notícia relevante encontrada nos últimos 30 dias."

    def test_saves_merged_history_to_cache(
        self, mocker, mock_cache_manager, sample_cached_articles, sample_new_articles
    ):
        """Tests that new articles are merged with history and saved."""

        # Arrange: Mock with existing cache and new articles.
        mock_cache_manager.load_cache.return_value = sample_cached_articles.copy()
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=sample_cached_articles.copy(),
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[{"url": "https://example.com/new1", "title": "New"}],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=sample_new_articles,
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.format_articles_output",
            return_value="Formatted",
        )

        # Act: Fetch news articles.
        fetch_news_articles.invoke({"query": "SUZB3"})

        # Assert: save_cache called with merged history.
        call_args = mock_cache_manager.save_cache.call_args
        saved_data = call_args[0][2]
        assert len(saved_data) == 3  # 2 cached + 1 new

    def test_uses_format_cache_key_for_filename(self, mocker, mock_cache_manager):
        """Tests that format_cache_key is used to generate cache filename."""

        # Arrange: Mock format_cache_key.
        mock_format_key = mocker.patch(
            "nexus_equitygraph.tools.news_tools.format_cache_key",
            return_value="petr4_news.json",
        )
        mock_cache_manager.load_cache.return_value = []
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=[],
        )

        # Act: Fetch news articles.
        fetch_news_articles.invoke({"query": "PETR4"})

        # Assert: format_cache_key called with correct args.
        mock_format_key.assert_called_once_with("PETR4", "news.json")
        mock_cache_manager.load_cache.assert_called_once_with("news", "petr4_news.json")

    def test_skips_malformed_cache_items_for_known_urls(self, mocker, mock_cache_manager):
        """Tests that malformed cache items are skipped when building known_urls."""

        # Arrange: Cache with malformed items (missing url key).
        malformed_cache = [
            {"url": "https://valid.com/article"},
            {"title": "Missing URL"},  # No url key
            "not a dict",  # Not a dict
            {"url": "https://another.com/article"},
        ]
        mock_cache_manager.load_cache.return_value = malformed_cache
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.filter_recent_articles",
            return_value=[],
        )
        mock_search = mocker.patch(
            "nexus_equitygraph.tools.news_tools.search_news_ddgs",
            return_value=[],
        )
        mocker.patch(
            "nexus_equitygraph.tools.news_tools.scrape_article_urls",
            return_value=[],
        )

        # Act: Fetch news articles.
        fetch_news_articles.invoke({"query": "CSAN3"})

        # Assert: Only valid URLs are in known_urls.
        call_args = mock_search.call_args
        known_urls = call_args[0][1]
        assert len(known_urls) == 2
        assert "https://valid.com/article" in known_urls
        assert "https://another.com/article" in known_urls
