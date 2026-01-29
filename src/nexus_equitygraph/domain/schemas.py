"""Schemas for structured LLM outputs."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class MetricOutput(BaseModel):
    """Schema for a single financial metric output."""

    name: str = Field(..., description="Name of the metric (e.g., 'P/E Ratio', 'Net Margin')")
    value: Union[float, str] = Field(..., description="Numeric value or string representation if qualitative")
    unit: Optional[str] = Field(None, description="Unit of the metric (e.g., '%', 'BRL', 'x')")
    period: Optional[str] = Field(None, description="Time period associated with the metric")
    description: Optional[str] = Field(None, description="Brief explanation of the metric")


class AnalysisOutput(BaseModel):
    """Schema for specialist agent analysis output (Fundamentalist, Quantitative, Sentiment, Risk)."""

    summary: str = Field(..., description="Executive summary of the analysis")
    details: str = Field(..., description="Detailed analysis in markdown format")
    metrics: List[MetricOutput] = Field(default_factory=list, description="Key metrics extracted or calculated")
    sources: Optional[List[str]] = Field(default_factory=list, description="List of data sources used")


class ReviewerOutput(BaseModel):
    """Schema for reviewer agent feedback output."""

    approved: bool = Field(..., description="Whether the analysis is approved (True) or needs revision (False)")
    comments: List[str] = Field(..., description="List of specific comments or critiques")
    recommendations: List[str] = Field(
        default_factory=list, description="List of actionable recommendations for improvement"
    )
