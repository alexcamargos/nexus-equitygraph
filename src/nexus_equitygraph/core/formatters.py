"""Output formatters for Nexus EquityGraph."""

import datetime
from pathlib import Path
from typing import Dict, Protocol, Sequence, runtime_checkable

from .configs import DirectoryConfigs
from .text_utils import truncate_text


@runtime_checkable
class ArticleLike(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for article-like objects with required attributes."""

    title: str
    url: str
    text: str
    timestamp: str


def normalize_article(article: ArticleLike | Dict) -> Dict[str, str]:
    """Normalize article data from ArticleLike or Dict to a standard Dict format.

    Args:
        article: An ArticleLike object or a dictionary with article data.

    Returns:
        A dictionary with standardized keys: title, url, text, timestamp.
    """

    if isinstance(article, dict):
        return {
            "title": article.get("title", "No Title"),
            "url": article.get("url", ""),
            "text": article.get("text", ""),
            "timestamp": article.get("timestamp", ""),
        }

    return {
        "title": article.title,
        "url": article.url,
        "text": article.text,
        "timestamp": article.timestamp,
    }


def format_single_article(article: Dict[str, str]) -> str:
    """Format a single article into markdown.

    Args:
        article: A normalized article dictionary with title, url, text, timestamp.

    Returns:
        A markdown-formatted string representing the article.
    """

    return "\n".join(
        [
            f"#### {article['title']}",
            f"**Source:** {article['url']}",
            f"**Date:** {article['timestamp']}",
            f"{article['text']}\n",
            "---",
        ]
    )


def format_articles_output(
    articles: Sequence[ArticleLike | Dict],
    header: str | None = None,
    snippet: bool = False,
    limit: int = 2_500,
) -> str:
    """Format a list of articles into a readable markdown string.

    Orchestrates normalization, truncation, and formatting of articles.

    Args:
        articles: Sequence of ArticleLike objects or dictionaries.
        header: Optional header text for the output section. Defaults to None.
        snippet: Whether to truncate article text. Defaults to False.
        limit: Maximum text length when snippet is True. Defaults to 2500.

    Returns:
        A markdown-formatted string containing all articles.
    """

    output: list[str] = []

    if header:
        output.append(f"### {header}\n")

    for article in articles:
        normalized = normalize_article(article)

        if snippet:
            normalized["text"] = truncate_text(normalized["text"], limit)

        output.append(format_single_article(normalized))

    return "\n".join(output)


def format_final_report(
    ticker: str,
    body: str,
    metadata: Dict[str, str] | None = None,
    template_path: Path | None = None,
) -> str:
    """Formats the final report using an external markdown template.

    Args:
        ticker: The ticker symbol analyzed.
        body: The main content of the report.
        metadata: Optional metadata (company name, sector, etc.).
        template_path: Optional path to the report template file.

    Returns:
        The formatted report string.
    """

    # Determine template path, use default if not provided.
    target_path = template_path or DirectoryConfigs().REPORT_TEMPLATE_FILE

    # Load template content
    try:
        template_content = target_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"# Error: Report template not found at {target_path}\n\n{body}"

    meta = metadata or {}

    # Prepare context for replacement
    context = {
        "{company}": meta.get("company_name", "N/A"),
        "{activity}": meta.get("activity", "N/A"),
        "{sector}": meta.get("sector", "N/A"),
        "{ticker}": ticker,
        "{timestamp}": datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        "{body}": body,
    }

    # Perform replacements in the template.
    formatted = template_content
    for placeholder, value in context.items():
        formatted = formatted.replace(placeholder, value)

    return formatted
