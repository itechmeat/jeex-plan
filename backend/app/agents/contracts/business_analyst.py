"""
Business Analyst agent contracts.
Handles project description, problem analysis, and business requirements.
"""

from typing import Dict, List, Optional, Any
from pydantic import Field
from .base import AgentInput, AgentOutput


class BusinessAnalystInput(AgentInput):
    """Input data for Business Analyst agent."""

    idea_description: str = Field(..., description="Initial project idea description")
    user_clarifications: Optional[Dict[str, Any]] = Field(
        None, description="User answers to clarifying questions"
    )
    target_audience: Optional[str] = Field(None, description="Known target audience")
    business_goals: Optional[List[str]] = Field(
        None, description="Known business objectives"
    )
    constraints: Optional[List[str]] = Field(
        None, description="Known constraints or limitations"
    )

    model_config = {"extra": "forbid"}


class BusinessAnalystOutput(AgentOutput):
    """Output from Business Analyst agent."""

    key_facts: List[str] = Field(
        ..., description="Extracted key facts for vector storage"
    )
    problem_statement: str = Field(..., description="Clear problem statement")
    target_audience_analysis: str = Field(..., description="Target audience analysis")
    success_metrics: List[str] = Field(..., description="Proposed success metrics")
    business_model_suggestions: List[str] = Field(
        ..., description="Business model recommendations"
    )
    risk_analysis: List[str] = Field(
        ..., description="Identified risks and mitigation strategies"
    )
    clarifying_questions: List[str] = Field(
        default_factory=list, description="Questions for user to improve clarity"
    )

    model_config = {"extra": "forbid"}
