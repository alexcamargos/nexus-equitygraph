"""Tests for the Quantitative Agent."""

import pytest
from nexus_equitygraph.agents import quantitative_node

@pytest.mark.smoke
def test_quantitative_agent_execution(base_state):
    """Test the Quantitative Agent in isolation."""
    
    result = quantitative_node(base_state)
    assert "analyses" in result
    assert result["analyses"][0].agent_name == "Vector"
