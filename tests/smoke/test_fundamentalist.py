import pytest
from nexus_equitygraph.agents.fundamentalist import fundamentalist_node
from nexus_equitygraph.domain.state import MarketAgentState

@pytest.mark.smoke
def test_fundamentalist_agent_execution(base_state):
    """Test the Fundamentalist Agent in isolation."""
    
    # Setup minimal state using shared fixture
    # Note: This calls the real agent which calls LLMs/APIs.
    # It requires credentials to be set in environment variables.
    result = fundamentalist_node(base_state)
    
    # Assertions
    assert "analyses" in result
    analysis = result["analyses"][0]
    assert analysis.agent_name == "Graham"
    assert analysis.ticker == "WEGE3"
    assert len(analysis.metrics) > 0
