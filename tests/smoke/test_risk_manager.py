"""Tests for the Risk Manager Agent."""

import pytest
from nexus_equitygraph.agents import risk_manager_node

@pytest.mark.smoke
def test_risk_manager_agent_execution(base_state):
    """Test the Risk Manager Agent in isolation."""
    
    result = risk_manager_node(base_state)
    assert "analyses" in result
    assert result["analyses"][0].agent_name == "Sentry"
