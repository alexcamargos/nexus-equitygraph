"""Connectivity smoke tests for Nexus Equity Graph external services.

These tests verify that the application can connect to external services like
LLM providers, CVM, News sources, and Yahoo Finance. They are slow and
depend on network availability.
"""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from nexus_equitygraph.core import create_llm_provider, get_http_client, settings
from nexus_equitygraph.services import CVMClient, resolve_name_from_ticker, search_news_ddgs


@pytest.mark.smoke
def test_llm_connectivity():
    """Verifies connectivity to the configured LLM provider."""
    try:
        model_name = settings.ollama_model_reasoning or settings.ollama_default_model
        llm = create_llm_provider(temperature=0.0, model_name=model_name)
        messages = [
            SystemMessage(content="You are a senior financial analyst. Answer concisely."),
            HumanMessage(content="sanity check"),
        ]
        response = llm.invoke(messages)
        assert response.content, "LLM returned empty content"
    except Exception as e:
        pytest.fail(f"LLM connectivity failed: {e}")


@pytest.mark.smoke
def test_http_client_connectivity():
    """Verifies the HTTP client can reach the internet."""
    client = get_http_client()
    try:
        # Test with a reliable endpoint
        response = client.get("https://httpbin.org/get")
        assert response.status_code == 200, f"HTTP check failed with status {response.status_code}"
    except Exception as e:
        pytest.fail(f"HTTP client connectivity failed: {e}")


@pytest.mark.smoke
def test_cvm_connectivity():
    """Verifies connectivity to CVM services (or cache)."""
    cvm_client = CVMClient()
    try:
        # Test cadastral data fetch (lightweight operation)
        df = cvm_client.get_cadastral_info()
        assert df is not None, "CVM client returned None for cadastral info"
        assert not df.empty, "CVM client returned empty DataFrame"
    except Exception as e:
        pytest.fail(f"CVM connectivity failed: {e}")


@pytest.mark.smoke
def test_news_connectivity():
    """Verifies connectivity to DuckDuckGo News search."""
    try:
        candidates = search_news_ddgs("Petrobras PETR4", set(), recent_count=0, max_results=5)
        # We might not find news, but it shouldn't raise an exception
        # If the API changes or is blocked, this helps detect it
        assert isinstance(candidates, list), "search_news_ddgs should return a list"
    except Exception as e:
        pytest.fail(f"News search connectivity failed: {e}")


@pytest.mark.smoke
def test_market_resolver_connectivity():
    """Verifies connectivity to Yahoo Finance via Market Resolver."""
    try:
        # Test ticker resolution
        result = resolve_name_from_ticker("PETR4")
        assert result is not None, "Could not resolve PETR4"
        assert "PETROBRAS" in result.upper() or "PETRÓLEO" in result.upper(), f"Unexpected resolution: {result}"
    except Exception as e:
        pytest.fail(f"Market resolver connectivity failed: {e}")
