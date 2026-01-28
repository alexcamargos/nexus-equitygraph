"""Tests for the Sentiment Agent."""

import pytest
from nexus_equitygraph.agents import sentiment_node

@pytest.mark.smoke
def test_sentiment_agent_execution(base_state):
    """Test the Sentiment Agent in isolation."""
    
    result = sentiment_node(base_state)
    assert "analyses" in result
    assert result["analyses"][0].agent_name == "Sonar"
