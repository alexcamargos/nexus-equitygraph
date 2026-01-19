"""News search and scraping service for Nexus EquityGraph."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

import requests
from ddgs.ddgs import DDGS
from loguru import logger

from nexus_equitygraph.core.http_client import HttpClient, get_http_client
from nexus_equitygraph.core.text_utils import extract_clean_text_from_html
from nexus_equitygraph.domain.state import NewsArticle

ALLOWLIST_DOMAINS: List[str] = [
    "reuters.com",
    "bloomberg.com",
    "braziljournal.com",
    "folha.uol.com.br",
    "estadao.com.br",
    "einvestidor.estadao.com.br",
    "valor.globo.com",
    "pipelinevalor.globo.com",
    "infomoney.com.br",
    "exame.com",
    "suno.com.br",
    "bloomberglinea.com.br",
    "cnnbrasil.com.br",
    "moneytimes.com.br",
    "seudinheiro.com",
    "neofeed.com.br",
    "wsj.com",
    "cnbc.com",
    "ft.com",
]


def fetch_url_content(
    http_client: HttpClient,
    url: str,
    title: str,
) -> Optional[NewsArticle]:
    """Fetch and process content from a URL.

    Args:
        http_client: The HTTP client to use for requests.
        url: The URL to fetch.
        title: The title of the article.

    Returns:
        A NewsArticle object if successful; None otherwise.
    
    Raises:
        requests.exceptions.RequestException: For network-related errors.
    """

    try:
        response = http_client.get(url)

        if response.status_code == 200:
            text = extract_clean_text_from_html(response.text)

            if text and len(text) > 100:
                return NewsArticle(
                    title=title,
                    url=url,
                    text=text,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

        logger.warning(f"Failed to fetch {url}: Status code {response.status_code}")
        return None

    except requests.exceptions.RequestException as error:
        logger.error(f"Error fetching URL {url}: {error}")
        return None


def filter_recent_articles(articles: List[Dict], days: int = 30) -> List[Dict]:
    """Filter articles to only include those within the specified time window.

    Args:
        articles: List of article dictionaries with 'date' or 'cached_at' fields.
        days: Number of days to look back. Defaults to 30.

    Returns:
        List of articles within the time window.
    
    Raises:
        ValueError: If date parsing fails.
        TypeError: If date fields are of incorrect type.
    """

    recent = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    for item in articles:
        ref_date_str = item.get("date") or item.get("cached_at")
        if not ref_date_str:
            continue

        try:
            ref_date = datetime.fromisoformat(ref_date_str)
            if ref_date.tzinfo is None:
                ref_date = ref_date.replace(tzinfo=timezone.utc)

            if ref_date > cutoff_date:
                recent.append(item)
        except (ValueError, TypeError):
            pass  # Skip articles with invalid dates

    return recent


def search_news_ddgs(
    query: str,
    known_urls: Set[str],
    recent_count: int = 0,
    max_results: int = 50,
) -> List[Dict]:
    """Search for news articles using DuckDuckGo and filter by allowlist.

    Args:
        query: The search query string.
        known_urls: Set of URLs already in the cache to skip.
        recent_count: Number of recent articles already available (for fallback logic).
        max_results: Maximum results to fetch from DDGS. Defaults to 50.

    Returns:
        List of candidate articles to scrape.

    Raises:
        Exception: Propagates DDGS exceptions to caller.
    """

    candidates = []

    with DDGS() as ddgs:
        ddg_results = list(ddgs.news(query, region="br-pt", max_results=max_results))

        for result in ddg_results:
            url = result.get("url") or result.get("link")
            if not url or url in known_urls:
                continue

            # Filter domains based on allowlist.
            if any(domain in url for domain in ALLOWLIST_DOMAINS):
                candidates.append(
                    {
                        "url": url,
                        "title": result.get("title"),
                        "date": result.get("date"),
                        "source": result.get("source"),
                    }
                )

        # Fallback if allowlist yields few results and we don't have recent articles.
        if len(candidates) < 3 and recent_count < 3:
            for result in ddg_results[:10]:
                url = result.get("url") or result.get("link")
                if url and url not in known_urls and url not in {candidate["url"] for candidate in candidates}:
                    candidates.append(
                        {
                            "url": url,
                            "title": result.get("title"),
                            "date": result.get("date"),
                            "source": result.get("source"),
                        }
                    )

    return candidates


def scrape_article_urls(
    candidates: List[Dict],
    limit: int,
    max_workers: int = 10,
) -> List[Dict]:
    """Scrape article content from URLs in parallel.

    Args:
        candidates: List of candidate articles with 'url' and 'title' keys.
        limit: Maximum number of articles to scrape successfully.
        max_workers: Number of parallel workers. Defaults to 10.

    Returns:
        List of article dictionaries with scraped content.
    """

    if not candidates:
        return []

    logger.info(f"Iniciando extração de texto (Scraping) de {len(candidates)} URLs...")

    new_articles = []
    http_client = get_http_client()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(fetch_url_content, http_client, item["url"], item["title"]): item for item in candidates
        }

        for future in as_completed(future_map):
            item_meta = future_map[future]
            result = future.result()

            if result:
                article_dict = result.model_dump()
                article_dict["source"] = item_meta.get("source")
                article_dict["cached_at"] = datetime.now(timezone.utc).isoformat()

                new_articles.append(article_dict)

                if len(new_articles) >= limit:
                    break

    return new_articles
