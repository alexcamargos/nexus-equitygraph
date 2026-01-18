"""Domain state definitions for the Market Analysis LangGraph graph."""

import operator
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FinancialMetric(BaseModel):
    """Represents an extracted or calculated financial metric."""

    name: str = Field(..., description="Metric name (e.g., P/E, ROE, VaR)")
    value: float | str = Field(..., description="The numerical value or string representation of the metric")
    unit: Optional[str] = Field(None, description="Unit (%, BRL, USD, points)")
    period: Optional[str] = Field(None, description="Reference period (e.g., 2023, 4Q23)")
    description: Optional[str] = Field(None, description="Brief explanation of the metric")


class ReviewFeedback(BaseModel):
    """Feedback structure from the reviewer agent."""

    agent_name: str = Field(..., description="Reviewer agent identifier")
    approved: bool = Field(..., description="Whether the analysis was approved or requires revision")
    comments: List[str] = Field(default_factory=list, description="List of comments or critiques")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions for correction")


class AgentAnalysis(BaseModel):
    """Generic structure for a specialist agent's output."""

    agent_name: str = Field(..., description="Agent identifier (e.g., fundamentalist)")
    ticker: str = Field(..., description="Ticker of the analyzed asset")
    summary: str = Field(..., description="Executive summary of the agent's analysis")
    details: str = Field(..., description="In-depth analysis content, formatted in Markdown")
    metrics: List[FinancialMetric] = Field(default_factory=list, description="Relevant identified metrics")
    sources: List[str] = Field(default_factory=list, description="Sources used (URLs, Documents)")
    timestamp: str = Field(..., description="Timestamp of analysis generation (ISO 8601 format)")


class MarketAgentState(BaseModel):
    """Global state of the LangGraph graph."""

    ticker: str = Field(..., description="Ticker of the asset being analyzed")
    analyses: Annotated[List[AgentAnalysis], operator.add] = Field(
        default_factory=list, description="Accumulated list of specialist analyses"
    )
    feedback: Optional[ReviewFeedback] = Field(None, description="Reviewer feedback, if any")
    final_report: Optional[str] = Field(None, description="Final consolidated report")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    iteration: int = Field(..., description="Current execution cycle count to prevent infinite recursion")
    messages: Annotated[List[Any], operator.add] = Field(
        default_factory=list, description="Message history (LangChain/LangGraph standard)"
    )
