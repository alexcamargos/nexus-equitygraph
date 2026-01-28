"""Tests for the Reviewer Agent."""

import pytest
from nexus_equitygraph.agents import reviewer_node
from nexus_equitygraph.domain.state import AgentAnalysis

@pytest.mark.smoke
def test_reviewer_agent_execution(base_state):
    """Test the Reviewer Agent logic."""
    
    # Reviewer needs input analyses
    fake_analysis = AgentAnalysis(
        agent_name="MockAgent",
        ticker="WEGE3",
        summary="Test Summary",
        details="Test Details",
        metrics=[],
        sources=[],
        timestamp="2025-01-01"
    )
    base_state.analyses.append(fake_analysis)
    
    result = reviewer_node(base_state)
    assert "feedback" in result
    assert result["feedback"].agent_name == "Reviewer"
