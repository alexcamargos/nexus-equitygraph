"""Tests for the domain state models in nexus_equitygraph.domain.state module."""

import operator
from typing import get_type_hints

import pytest
from pydantic import ValidationError

from nexus_equitygraph.domain.state import (
    AgentAnalysis,
    FinancialMetric,
    MarketAgentState,
    NewsArticle,
    ReviewFeedback,
)


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

        # Arrange & Act: Create metric with string value.
        metric = FinancialMetric(
            name="Rating", value="AAA", unit=None, period=None, description=None
        )

        # Assert: String value is accepted.
        assert metric.value == "AAA"

    def test_required_fields(self):
        """Tests that name and value are required."""

        with pytest.raises(ValidationError):
            FinancialMetric(name="Incomplete")

    def test_optional_fields_default_to_none(self):
        """Tests that optional fields default to None when not provided."""

        # Arrange: Minimal metric without optional fields.
        name = "ROE"
        value = 15.5

        # Act: Create metric without optional fields (Pydantic should default to None).
        metric = FinancialMetric(name=name, value=value)  # type: ignore[call-arg]

        # Assert: Optional fields default to None.
        assert metric.unit is None
        assert metric.period is None
        assert metric.description is None

    def test_value_can_be_zero(self):
        """Tests that value can be zero."""

        # Arrange: Metric with zero value.
        name = "Growth Rate"
        value = 0.0

        # Act: Create metric with explicit None for optionals.
        metric = FinancialMetric(
            name=name, value=value, unit=None, period=None, description=None
        )

        # Assert: Zero value is accepted.
        assert metric.value == 0.0

    def test_value_can_be_negative(self):
        """Tests that value can be negative (e.g., losses)."""

        # Arrange: Metric with negative value.
        name = "Net Income"
        value = -500000.0
        unit = "BRL"

        # Act: Create metric with explicit None for optionals.
        metric = FinancialMetric(
            name=name, value=value, unit=unit, period=None, description=None
        )

        # Assert: Negative value is accepted.
        assert metric.value == -500000.0
        assert metric.unit == "BRL"

    def test_full_metric_with_all_fields(self):
        """Tests creation of a metric with all fields populated."""

        # Arrange: All fields provided.
        name = "P/E Ratio"
        value = 12.5
        unit = "x"
        period = "4Q23"
        description = "Price to Earnings ratio"

        # Act: Create metric.
        metric = FinancialMetric(
            name=name, value=value, unit=unit, period=period, description=description
        )

        # Assert: All fields populated correctly.
        assert metric.name == name
        assert metric.value == value
        assert metric.unit == unit
        assert metric.period == period
        assert metric.description == description


class TestNewsArticle:
    """Test suite for NewsArticle model."""

    def test_valid_article(self):
        """Tests creation of a valid news article."""

        # Arrange: Valid article data.
        title = "Petrobras announces quarterly results"
        url = "https://example.com/news/petrobras"
        text = "Petrobras reported strong earnings..."
        timestamp = "2025-01-15T10:30:00Z"

        # Act: Create article.
        article = NewsArticle(title=title, url=url, text=text, timestamp=timestamp)

        # Assert: All fields populated correctly.
        assert article.title == title
        assert article.url == url
        assert article.text == text
        assert article.timestamp == timestamp

    def test_required_fields_title(self):
        """Tests that title is required."""

        # Arrange: Missing title.
        data = {
            "url": "https://example.com",
            "text": "Content",
            "timestamp": "2025-01-15T10:30:00Z",
        }

        # Act & Assert: ValidationError raised.
        with pytest.raises(ValidationError):
            NewsArticle(**data)

    def test_required_fields_url(self):
        """Tests that url is required."""

        # Arrange: Missing url.
        data = {
            "title": "Title",
            "text": "Content",
            "timestamp": "2025-01-15T10:30:00Z",
        }

        # Act & Assert: ValidationError raised.
        with pytest.raises(ValidationError):
            NewsArticle(**data)

    def test_required_fields_text(self):
        """Tests that text is required."""

        # Arrange: Missing text.
        data = {
            "title": "Title",
            "url": "https://example.com",
            "timestamp": "2025-01-15T10:30:00Z",
        }

        # Act & Assert: ValidationError raised.
        with pytest.raises(ValidationError):
            NewsArticle(**data)

    def test_required_fields_timestamp(self):
        """Tests that timestamp is required."""

        # Arrange: Missing timestamp.
        data = {
            "title": "Title",
            "url": "https://example.com",
            "text": "Content",
        }

        # Act & Assert: ValidationError raised.
        with pytest.raises(ValidationError):
            NewsArticle(**data)

    def test_empty_strings_allowed(self):
        """Tests that empty strings are technically allowed (no min_length constraint)."""

        # Arrange: Empty string values.
        title = ""
        url = ""
        text = ""
        timestamp = ""

        # Act: Create article with empty strings.
        article = NewsArticle(title=title, url=url, text=text, timestamp=timestamp)

        # Assert: Empty strings accepted.
        assert article.title == ""
        assert article.url == ""


class TestAgentAnalysis:
    """Test suite for AgentAnalysis model."""

    def test_valid_analysis(self):
        """Tests creation of a valid analysis."""

        # Arrange & Act: Create analysis with required fields (default_factory for lists).
        analysis = AgentAnalysis(  # type: ignore[call-arg]
            agent_name="Graham",
            ticker="PETR4",
            summary="Good fundamentals",
            details="# Analysis\n...",
            timestamp="2023-10-27T10:00:00Z",
        )

        # Assert: Fields populated correctly, lists default to empty.
        assert analysis.agent_name == "Graham"
        assert analysis.metrics == []  # default_factory check
        assert analysis.sources == []  # default_factory check

    def test_markdown_format_description(self):
        """Verifies the field description mentions Markdown (metadata check)."""

        schema = AgentAnalysis.model_json_schema()
        details_desc = schema["properties"]["details"]["description"]
        assert "Markdown" in details_desc

    def test_required_fields(self):
        """Tests that essential fields are required."""

        # Arrange: Only agent_name provided.

        # Act & Assert: ValidationError raised for missing fields.
        with pytest.raises(ValidationError):
            AgentAnalysis(agent_name="Graham")  # Missing ticker, summary, etc.  # type: ignore[call-arg]

    def test_analysis_with_metrics(self):
        """Tests creation of analysis with populated metrics list."""

        # Arrange: Analysis with metrics.
        metrics = [
            FinancialMetric(
                name="ROE", value=15.5, unit="%", period=None, description=None
            ),
            FinancialMetric(
                name="P/E", value=12.0, unit="x", period=None, description=None
            ),
        ]

        # Act: Create analysis with metrics.
        analysis = AgentAnalysis(
            agent_name="Graham",
            ticker="PETR4",
            summary="Strong fundamentals",
            details="# Analysis\nDetailed content...",
            metrics=metrics,
            sources=[],
            timestamp="2025-01-15T10:00:00Z",
        )

        # Assert: Metrics populated correctly.
        assert len(analysis.metrics) == 2
        assert analysis.metrics[0].name == "ROE"
        assert analysis.metrics[1].name == "P/E"

    def test_analysis_with_sources(self):
        """Tests creation of analysis with populated sources list."""

        # Arrange: Analysis with sources.
        sources = [
            "https://ri.petrobras.com.br",
            "CVM Document 12345",
        ]

        # Act: Create analysis with sources.
        analysis = AgentAnalysis(
            agent_name="Graham",
            ticker="PETR4",
            summary="Strong fundamentals",
            details="# Analysis\nDetailed content...",
            metrics=[],
            sources=sources,
            timestamp="2025-01-15T10:00:00Z",
        )

        # Assert: Sources populated correctly.
        assert len(analysis.sources) == 2
        assert "ri.petrobras.com.br" in analysis.sources[0]


class TestMarketAgentState:
    """Test suite for MarketAgentState model."""

    def test_default_values(self):
        """Tests default values for lists and optionals."""

        # Arrange & Act: Create state with only required fields (Pydantic defaults).
        state = MarketAgentState(ticker="VALE3", iteration=1)  # type: ignore[call-arg]

        # Assert: Default values are correct.
        assert state.analyses == []
        assert state.messages == []
        assert state.feedback is None
        assert state.final_report is None
        assert state.metadata is None

    def test_required_fields(self):
        """Tests that ticker and iteration are required."""

        with pytest.raises(ValidationError):
            MarketAgentState(ticker="VALE3")  # Missing iteration # type: ignore[call-arg]

    def test_reducer_configuration(self):
        """Verifies that the operator.add reducer is correctly configured in annotations."""

        # Arrange: Get type hints with extras.
        type_hints = get_type_hints(MarketAgentState, include_extras=True)

        # Act: Extract metadata from annotated types.
        analyses_metadata = type_hints["analyses"].__metadata__
        messages_metadata = type_hints["messages"].__metadata__

        # Assert: operator.add is configured as reducer.
        assert operator.add in analyses_metadata
        assert operator.add in messages_metadata

    def test_analyses_reducer_behavior(self):
        """Tests that analyses list can be extended via reducer pattern."""

        # Arrange: Initial state and new analysis.
        state = MarketAgentState(
            ticker="PETR4",
            iteration=1,
            analyses=[],
            feedback=None,
            final_report=None,
            metadata=None,
        )
        new_analysis = AgentAnalysis(
            agent_name="Graham",
            ticker="PETR4",
            summary="Good fundamentals",
            details="# Analysis",
            metrics=[],
            sources=[],
            timestamp="2025-01-15T10:00:00Z",
        )

        # Act: Simulate reducer by using operator.add.
        combined = operator.add(state.analyses, [new_analysis])

        # Assert: Lists are combined.
        assert len(combined) == 1
        assert combined[0].agent_name == "Graham"

    def test_state_with_feedback(self):
        """Tests state creation with feedback populated."""

        # Arrange: Feedback object.
        feedback = ReviewFeedback(
            agent_name="Reviewer",
            approved=False,
            comments=["Needs more data"],
        )

        # Act: Create state with feedback.
        state = MarketAgentState(
            ticker="VALE3",
            iteration=2,
            feedback=feedback,
            final_report=None,
            metadata=None,
        )

        # Assert: Feedback is populated.
        assert state.feedback is not None
        feedback_result = state.feedback  
        assert feedback_result.agent_name == "Reviewer"  #pylint: disable=E1101
        assert not feedback_result.approved  # pylint: disable=E1101

    def test_state_with_final_report(self):
        """Tests state creation with final report."""

        # Arrange: Final report content.
        final_report = "# Final Analysis Report\n\nConclusion: Buy recommendation."

        # Act: Create state with final report.
        state = MarketAgentState(
            ticker="WEGE3",
            iteration=3,
            feedback=None,
            final_report=final_report,
            metadata=None,
        )

        # Assert: Final report is populated.
        assert state.final_report is not None
        assert "Buy recommendation" in state.final_report

    def test_state_with_metadata(self):
        """Tests state creation with metadata dictionary."""

        # Arrange: Metadata dictionary.
        metadata = {
            "execution_time_ms": 1500,
            "model": "gpt-4",
            "temperature": 0.7,
        }

        # Act: Create state with metadata.
        state = MarketAgentState(
            ticker="ITUB4",
            iteration=1,
            feedback=None,
            final_report=None,
            metadata=metadata,
        )

        # Assert: Metadata is populated correctly.
        assert state.metadata is not None
        assert state.metadata["execution_time_ms"] == 1500
        assert state.metadata["model"] == "gpt-4"


class TestReviewFeedback:
    """Test suite for ReviewFeedback model."""

    def test_valid_feedback(self):
        """Tests creation of a valid feedback."""

        # Arrange: Valid feedback data.
        agent_name = "Reviewer1"
        approved = False
        comments = ["Needs more data."]
        recommendations = ["Include recent market trends."]

        # Act: Create feedback.
        feedback = ReviewFeedback(
            agent_name=agent_name,
            approved=approved,
            comments=comments,
            recommendations=recommendations,
        )

        # Assert: All fields populated correctly.
        assert feedback.agent_name == "Reviewer1"
        assert not feedback.approved
        assert len(feedback.comments) == 1
        assert len(feedback.recommendations) == 1

    def test_default_lists(self):
        """Tests default values for lists."""

        # Arrange: Minimal required fields.
        agent_name = "Reviewer1"
        approved = True

        # Act: Create feedback without optional lists.
        feedback = ReviewFeedback(agent_name=agent_name, approved=approved)  # type: ignore[call-arg]

        # Assert: Lists default to empty.
        assert feedback.comments == []
        assert feedback.recommendations == []

    def test_required_fields_agent_name(self):
        """Tests that agent_name is required."""

        # Arrange: Missing agent_name.

        # Act & Assert: ValidationError raised.
        with pytest.raises(ValidationError):
            ReviewFeedback(approved=True)  # Missing agent_name # type: ignore[call-arg]

    def test_required_fields_approved(self):
        """Tests that approved is required."""

        # Arrange: Missing approved.

        # Act & Assert: ValidationError raised.
        with pytest.raises(ValidationError):
            ReviewFeedback(agent_name="Reviewer1")  # Missing approved # type: ignore[call-arg]

    def test_feedback_with_multiple_comments(self):
        """Tests feedback with multiple comments and recommendations."""

        # Arrange: Multiple items in lists.
        comments = [
            "Missing risk analysis",
            "Outdated financial data",
            "No competitive analysis",
        ]
        recommendations = [
            "Add VaR calculation",
            "Update to Q4 2024 data",
        ]

        # Act: Create feedback with multiple items.
        feedback = ReviewFeedback(
            agent_name="SeniorReviewer",
            approved=False,
            comments=comments,
            recommendations=recommendations,
        )

        # Assert: All items preserved.
        assert len(feedback.comments) == 3
        assert len(feedback.recommendations) == 2
        assert "VaR" in feedback.recommendations[0]
