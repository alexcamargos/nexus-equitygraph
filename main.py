"""Main entry point for Nexus Equity Graph application."""

import os
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

# Ensure src is in pythonpath to allow running directly without installation
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# pylint: disable=import-error,wrong-import-position
from nexus_equitygraph import __version__
from nexus_equitygraph.core import (
    create_llm_provider,
    get_http_client,
    get_json_cache_manager,
    normalize_company_name,
    settings,
)
from nexus_equitygraph.services import CVMClient, resolve_name_from_ticker, search_news_ddgs
from nexus_equitygraph.tools.news_tools import fetch_news_articles


def configure_logging():
    """Configures the logging format and level.

    Sets up loguru to display time, log level, function name, and message.
    """

    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )


def run_llm_smoke_test() -> bool:
    """Runs a connectivity test to validate LLM configuration.

    Returns:
        bool: True if test passed, False otherwise.
    """

    logger.info("=== LLM Smoke Test ===")

    try:
        llm = create_llm_provider(temperature=0.0)
        # Attempt a simple prompt to verify connectivity.
        model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "unknown")
        logger.info(f"LLM Initialized: {model_name}")

        messages = [
            SystemMessage(content="You are a senior financial analyst. Answer concisely."),
            HumanMessage(content="Define 'Free Cash Flow' in one sentence."),
        ]

        logger.info("Sending test prompt to LLM...")
        response = llm.invoke(messages)

        logger.success(f"LLM Response: {response.content[:100]}...")
        return True

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"LLM Smoke Test Failed: {e}")
        return False


def run_http_client_test() -> bool:
    """Tests HttpClient singleton functionality.

    Returns:
        bool: True if test passed, False otherwise.
    """

    logger.info("=== HTTP Client Test ===")

    try:
        client = get_http_client()
        logger.info(f"HttpClient initialized with timeout={client.timeout}s")

        # Test with a reliable endpoint
        response = client.get("https://httpbin.org/get")
        logger.success(f"HTTP GET test passed (status={response.status_code})")
        return True

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"HTTP Client Test Failed: {e}")
        return False


def run_cache_test() -> bool:
    """Tests cache manager functionality.

    Returns:
        bool: True if test passed, False otherwise.
    """

    logger.info("=== Cache Manager Test ===")

    try:
        cache_manager = get_json_cache_manager()
        logger.info(f"Cache base directory: {cache_manager.base_directory}")

        # Save and load test data
        test_data = {"test_key": "test_value", "timestamp": "2025-01-15T10:00:00Z"}
        cache_manager.save_cache("test", "smoke_test.json", test_data)
        logger.info("Test data saved to cache")

        loaded_data = cache_manager.load_cache("test", "smoke_test.json")
        if loaded_data and loaded_data.get("test_key") == "test_value":
            logger.success("Cache save/load test passed")
            return True
        else:
            logger.error("Cache data mismatch")
            return False

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Cache Manager Test Failed: {e}")
        return False


def run_market_resolver_test() -> bool:
    """Tests market resolver functionality.

    Returns:
        bool: True if test passed, False otherwise.
    """

    logger.info("=== Market Resolver Test ===")

    try:
        # Test ticker resolution
        test_cases = [
            ("PETR4", "Petrobras"),
            ("VALE3", "Vale"),
            ("ITUB4", "Itaú"),
        ]

        for ticker, expected_partial in test_cases:
            result = resolve_name_from_ticker(ticker)
            if result and expected_partial.lower() in result.lower():
                logger.info(f"  {ticker} -> {result}")
            else:
                logger.warning(f"  {ticker} -> {result or 'Not found'} (expected contains '{expected_partial}')")

        logger.success("Market resolver test completed")
        return True

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Market Resolver Test Failed: {e}")
        return False


def run_text_utils_test() -> bool:
    """Tests text utilities functionality.

    Returns:
        bool: True if test passed, False otherwise.
    """

    logger.info("=== Text Utils Test ===")

    try:
        test_cases = [
            ("PETROBRAS S.A.", "PETROBRAS"),
            ("Vale S/A", "VALE"),
            ("Banco Itaú Unibanco S.A.", "BANCO_ITAU_UNIBANCO"),
        ]

        for input_name, expected in test_cases:
            result = normalize_company_name(input_name)
            status = "✓" if expected in result else "✗"
            logger.info(f"  {status} '{input_name}' -> '{result}'")

        logger.success("Text utils test completed")
        return True

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Text Utils Test Failed: {e}")
        return False


def run_news_search_test() -> bool:
    """Tests news search functionality (DDGS).

    Returns:
        bool: True if test passed, False otherwise.
    """

    logger.info("=== News Search Test (DDGS) ===")

    try:
        # Search for news about a popular ticker
        candidates = search_news_ddgs("Petrobras PETR4", set(), recent_count=0, max_results=5)

        logger.info(f"Found {len(candidates)} news candidates")
        for candidate in candidates[:3]:
            logger.info(f"  - {candidate.get('title', 'No title')[:60]}...")

        logger.success("News search test completed")
        return True

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"News Search Test Failed: {e}")
        return False


def run_cvm_client_test() -> bool:
    """Tests CVM client functionality.

    Returns:
        bool: True if test passed, False otherwise.
    """

    logger.info("=== CVM Client Test ===")

    try:
        cvm_client = CVMClient()
        logger.info("CVMClient initialized")

        # Test cadastral data fetch (lightweight operation)
        # This tests the HTTP client integration and caching
        logger.info("Testing cadastral data fetch...")
        df = cvm_client.get_cadastral_info()

        if df is not None and len(df) > 0:
            logger.success(f"Fetched cadastral data: {len(df)} companies")
            logger.info(f"  Columns: {list(df.columns)[:5]}...")
            return True
        else:
            logger.warning("No cadastral data returned")
            return False

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"CVM Client Test Failed: {e}")
        return False


def run_news_tool_test() -> bool:
    """Tests the LangChain news tool integration.

    Returns:
        bool: True if test passed, False otherwise.
    """

    logger.info("=== News Tool Test (LangChain Integration) ===")

    try:
        # Invoke the tool with a simple query
        result = fetch_news_articles.invoke({"query": "Petrobras", "num_results": 2})

        if result and len(result) > 50:
            logger.success(f"News tool returned {len(result)} chars of formatted output")
            # Show first 200 chars of the result
            preview = result[:200].replace("\n", " ")
            logger.info(f"  Preview: {preview}...")
            return True
        else:
            logger.warning(f"News tool returned insufficient data: {result[:100] if result else 'None'}")
            return False

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"News Tool Test Failed: {e}")
        return False


def run_all_smoke_tests():
    """Runs all smoke tests and reports results."""

    logger.info(f"Starting Nexus Equity Graph v{__version__.__version__}")
    logger.info(f"Configuration: Provider={settings.provider.upper()}")
    logger.info("=" * 50)

    tests = [
        ("HTTP Client", run_http_client_test),
        ("Cache Manager", run_cache_test),
        ("Text Utils", run_text_utils_test),
        ("Market Resolver", run_market_resolver_test),
        ("News Search (DDGS)", run_news_search_test),
        ("CVM Client", run_cvm_client_test),
        ("LLM Provider", run_llm_smoke_test),
        ("News Tool (LangChain)", run_news_tool_test),
    ]

    results = {}
    for name, test_func in tests:
        logger.info("")
        try:
            results[name] = test_func()
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Unexpected error in {name}: {e}")
            results[name] = False

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("=== SMOKE TEST SUMMARY ===")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {status}: {name}")

    logger.info("")
    if passed == total:
        logger.success(f"All {total} tests passed!")
    else:
        logger.warning(f"{passed}/{total} tests passed")
        sys.exit(1)


def main():
    """Main entry point for the application."""

    configure_logging()
    run_all_smoke_tests()


if __name__ == "__main__":
    main()
