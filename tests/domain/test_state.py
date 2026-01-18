"""Tests for the domain state models in nexus_equitygraph.domain.state module."""

import operator
from typing import get_type_hints

import pytest
from pydantic import ValidationError

from nexus_equitygraph.domain.state import AgentAnalysis, FinancialMetric, MarketAgentState, ReviewFeedback


class TestFinancialMetric:
    """Test suite for FinancialMetric model."""

    def test_valid_metric(self):
        """Tests creation of a valid metric."""

        metric = FinancialMetric(name="ROE", value=15.5, unit="%", period="2023")
        assert metric.name == "ROE"
        assert metric.value == 15.5
        assert metric.unit == "%"

    def test_value_can_be_string(self):
        """Tests that value can be a string."""

        metric = FinancialMetric(name="Rating", value="AAA")
        assert metric.value == "AAA"

    def test_required_fields(self):
        """Tests that name and value are required."""

        with pytest.raises(ValidationError):
            FinancialMetric(name="Incomplete")

    def test_optional_fields_default_to_none(self):
        """Tests that optional fields default to None when not provided."""
        metric = FinancialMetric(name="ROE", value=15.5)
        assert metric.unit is None
        assert metric.period is None
        assert metric.description is None


class TestAgentAnalysis:
    """Test suite for AgentAnalysis model."""

    def test_valid_analysis(self):
        """Tests creation of a valid analysis."""

        analysis = AgentAnalysis(
            agent_name="Graham",
            ticker="PETR4",
            summary="Good fundamentals",
            details="# Analysis\n...",
            timestamp="2023-10-27T10:00:00Z",
        )

        assert analysis.agent_name == "Graham"
        assert analysis.metrics == []  # Default factory check
        assert analysis.sources == []  # Default factory check

    def test_markdown_format_description(self):
        """Verifies the field description mentions Markdown (metadata check)."""

        schema = AgentAnalysis.model_json_schema()
        details_desc = schema["properties"]["details"]["description"]
        assert "Markdown" in details_desc

    def test_required_fields(self):
        """Tests that essential fields are required."""

        with pytest.raises(ValidationError):
            AgentAnalysis(agent_name="Graham")  # Missing ticker, summary, etc.


class TestMarketAgentState:
    """Test suite for MarketAgentState model."""

    def test_default_values(self):
        """Tests default values for lists and optionals."""

        state = MarketAgentState(ticker="VALE3", iteration=1)

        assert state.analyses == []
        assert state.messages == []
        assert state.feedback is None
        assert state.final_report is None
        assert state.metadata is None

    def test_required_fields(self):
        """Tests that ticker and iteration are required."""

        with pytest.raises(ValidationError):
            MarketAgentState(ticker="VALE3")  # Missing iteration

    def test_reducer_configuration(self):
        """Verifies that the operator.add reducer is correctly configured in annotations."""

        type_hints = get_type_hints(MarketAgentState, include_extras=True)

        # Verify reducers are present in metadata
        assert operator.add in type_hints["analyses"].__metadata__
        assert operator.add in type_hints["messages"].__metadata__


class TestReviewFeedback:
    """Test suite for ReviewFeedback model."""

    def test_valid_feedback(self):
        """Tests creation of a valid feedback."""

        feedback = ReviewFeedback(
            agent_name="Reviewer1",
            approved=False,
            comments=["Needs more data."],
            recommendations=["Include recent market trends."],
        )

        assert feedback.agent_name == "Reviewer1"
        assert not feedback.approved
        assert len(feedback.comments) == 1
        assert len(feedback.recommendations) == 1

    def test_default_lists(self):
        """Tests default values for lists."""

        feedback = ReviewFeedback(agent_name="Reviewer1", approved=True)

        assert feedback.comments == []
        assert feedback.recommendations == []

    def test_required_fields(self):
        """Tests that agent_name and approved are required."""

        with pytest.raises(ValidationError):
            ReviewFeedback(approved=True)  # Missing agent_name

        with pytest.raises(ValidationError):
            ReviewFeedback(agent_name="Reviewer1")  # Missing approved
