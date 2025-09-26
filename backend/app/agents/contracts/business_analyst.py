"""
Business Analyst agent contracts.
Handles project description, problem analysis, and business requirements.
"""

from typing import Any

from pydantic import Field

from .base import AgentInput, AgentOutput


class BusinessAnalystInput(AgentInput):
    """Input data for Business Analyst agent."""

    idea_description: str = Field(..., description="Initial project idea description")
    user_clarifications: dict[str, Any] | None = Field(
        None, description="User answers to clarifying questions"
    )
    target_audience: str | None = Field(None, description="Known target audience")
    business_goals: list[str] | None = Field(
        None, description="Known business objectives"
    )
    constraints: list[str] | None = Field(
        None, description="Known constraints or limitations"
    )

    model_config = {"extra": "forbid"}


class BusinessAnalystOutput(AgentOutput):
    """Output from Business Analyst agent."""

    key_facts: list[str] = Field(
        ..., description="Extracted key facts for vector storage"
    )
    problem_statement: str = Field(..., description="Clear problem statement")
    target_audience_analysis: str = Field(..., description="Target audience analysis")
    success_metrics: list[str] = Field(..., description="Proposed success metrics")
    business_model_suggestions: list[str] = Field(
        ..., description="Business model recommendations"
    )
    risk_analysis: list[str] = Field(
        ..., description="Identified risks and mitigation strategies"
    )
    clarifying_questions: list[str] = Field(
        default_factory=list, description="Questions for user to improve clarity"
    )

    model_config = {"extra": "forbid"}
