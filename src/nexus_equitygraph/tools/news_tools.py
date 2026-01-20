"""News tools for LangChain agents."""

from typing import Any, Dict, List

from ddgs.exceptions import DDGSException
from langchain_core.tools import tool
from loguru import logger

from nexus_equitygraph.core.cache import get_json_cache_manager
from nexus_equitygraph.core.formatters import format_articles_output
from nexus_equitygraph.core.text_utils import format_cache_key
from nexus_equitygraph.services.news_search import filter_recent_articles, scrape_article_urls, search_news_ddgs

SEARCH_RESULT_LIMIT: int = 5


@tool
def fetch_news_articles(
    query: str,
    num_results: int = SEARCH_RESULT_LIMIT,
) -> str:
    """Fetch news articles related to a query using DuckDuckGo search.

    Orchestrates cache management, search, scraping, and formatting.

    Args:
        query (str): The search query.
        num_results (int): Number of search results to retrieve.

    Returns:
        str: Formatted string containing the news articles.

    Raises:
        DDGSException: Propagates DDGS exceptions to caller.
    """

    cache_manager = get_json_cache_manager()
    db_filename = format_cache_key(query, "news.json")

    # Load history and build dedup set of known URLs.
    cached_data = cache_manager.load_cache("news", db_filename)
    full_history: List[Dict[str, Any]] = cached_data if isinstance(cached_data, list) else []
    known_urls: set[str] = {
        item["url"] for item in full_history if isinstance(item, dict) and "url" in item
    }

    # Filter recent articles for context window
    recent_news = filter_recent_articles(full_history)

    # Search for new articles
    logger.info(f"Buscando notícias recentes para: {query} (Já temos {len(full_history)} no histórico)")

    try:
        candidates = search_news_ddgs(query, known_urls, len(recent_news))
    except DDGSException as error:
        logger.error(f"Erro na busca de notícias (DDGS): {error}")

        if recent_news:
            return format_articles_output(recent_news, "Histórico (Busca Falhou)")

        return f"Erro na busca e sem histórico: {error}"

    # Scrape new articles
    new_articles = scrape_article_urls(candidates, num_results)

    # Merge and save to cache
    if new_articles:
        logger.info(f"{len(new_articles)} novos artigos salvos no histórico.")
        full_history.extend(new_articles)
        cache_manager.save_cache("news", db_filename, full_history)
        recent_news.extend(new_articles)

    # Format output
    if not recent_news:
        return "Nenhuma notícia relevante encontrada nos últimos 30 dias."

    final_output = recent_news[-num_results:] if len(recent_news) > num_results else recent_news

    return format_articles_output(
        final_output,
        f"Notícias Recentes (<30 dias) - Total no Histórico: {len(full_history)}",
    )
