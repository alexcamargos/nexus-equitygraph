"""Text processing utilities for Nexus EquityGraph."""

import re
from typing import Any, Optional

import trafilatura
from loguru import logger

# Regular expressions, precompiled for performance, to clean company names.
RE_CLEAN_PUNCTUATION = re.compile(r"[\.\,\-]")
RE_REMOVE_CORP_SUFFIX = re.compile(r"\s+(S\s?A|S\/A|LTDA|HOLDING|PARTICIPACOES|PARTICIPAÇÕES)\b.*")
RE_CLEAN_WHITESPACE = re.compile(r"\s+")
RE_THINK_TAGS = re.compile(r"<think>.*?</think>", flags=re.DOTALL)


def normalize_company_name(name: Optional[str]) -> str:
    """Normalizes a company name by removing corporate suffixes and punctuation.

    Useful for matching across different data sources (CVM, YFinance, News).
    Ex: "WEG S.A." -> "WEG"

    Args:
        name (Optional[str]): Original company name.

    Returns:
        str: Normalized name in uppercase.
    """

    if not name:
        return ""

    clean = name.upper()
    clean = RE_CLEAN_PUNCTUATION.sub(" ", clean)
    clean = RE_REMOVE_CORP_SUFFIX.sub("", clean)

    # Remove extra spaces
    return " ".join(clean.split())


def format_cache_key(identifier: str, suffix: str) -> str:
    """Formats a string to be used as a safe filesystem cache key.

    Args:
        identifier (str): The base identifier (e.g., Ticker or Company Name).
        suffix (str): Suffix to append (e.g., 'financials_3y.pkl').

    Returns:
        str: A filesystem-safe filename.
    """

    safe_id = identifier.upper().replace(" ", "_").replace(".", "").replace("/", "")

    return f"{safe_id}_{suffix}"


def truncate_text(text: str, limit: int, suffix: str = "...") -> str:
    """Truncate text to a specified limit with an optional suffix.

    Args:
        text: The text to truncate.
        limit: Maximum character length before truncation.
        suffix: String to append when truncated. Defaults to "...".

    Returns:
        The original text if within limit, otherwise truncated text with suffix.
    """

    if len(text) <= limit:
        return text

    return text[:limit] + suffix


def extract_clean_text_from_html(html_content: str) -> str:
    """Extract and clean text from HTML content using trafilatura.

    Args:
        html_content: The HTML content to extract text from.

    Returns:
        The extracted and cleaned text, or empty string on failure.

    Raises:
        ValueError: If the HTML content is invalid.
        AttributeError: If the HTML content is not a string.
        Exception: For other unexpected errors.
    """

    try:
        cleaned_html = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=False,
            include_formatting=False,
            fast=True,
        )
        if not cleaned_html:
            return ""

        # Remove excessive whitespace and newlines.
        return RE_CLEAN_WHITESPACE.sub(" ", cleaned_html).strip()

    except (ValueError, AttributeError) as error:
        logger.error(f"Error extracting text from HTML: {error}")
        return ""
    except Exception as error:
        logger.error(f"Unexpected error extracting text from HTML: {error}")
        return ""


def cleanup_think_tags(content: str | Any) -> str:
    """Removes <think>...</think> tags from the content.

    Args:
        content (str | Any): The text content containing potential think tags.
                             Accepts Any to handle LangChain's complex content types.

    Returns:
        str: Cleaned content without the think tags.
    """

    if content is None:
        return ""

    if not isinstance(content, str):
        try:
            content = str(content)
        except (ValueError, TypeError, AttributeError) as error:
            logger.error(f"Failed to convert content to string in cleanup_think_tags: {error}")
            return ""

    return RE_THINK_TAGS.sub("", content).strip()


def clean_json_markdown(content: str) -> str:
    """Removes markdown code blocks (```json ... ```) from the content.

    Args:
        content (str): The text content containing markdown code blocks.

    Returns:
        str: Cleaned content with just the JSON string (or original if no markdown).
    """

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.replace("```", "").strip()

    return content
