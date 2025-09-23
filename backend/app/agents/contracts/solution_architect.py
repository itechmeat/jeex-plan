"""
Solution Architect agent contracts.
Handles technical architecture, technology stack, and system design.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from .base import AgentInput, AgentOutput


class SolutionArchitectInput(AgentInput):
    """Input data for Solution Architect agent."""

    project_description: str = Field(..., description="Complete project description from Business Analyst")
    user_tech_preferences: Optional[Dict[str, Any]] = Field(
        None, description="User's technology preferences or constraints"
    )
    scalability_requirements: Optional[str] = Field(None, description="Scalability requirements")
    team_size: Optional[int] = Field(None, description="Development team size")
    timeline: Optional[str] = Field(None, description="Project timeline constraints")
    budget_constraints: Optional[str] = Field(None, description="Budget limitations")

    model_config = {"extra": "forbid"}


class TechnologyChoice(BaseModel):
    """Technology selection with rationale."""

    name: str = Field(..., description="Technology name")
    category: str = Field(..., description="Technology category (frontend, backend, database, etc.)")
    rationale: str = Field(..., description="Why this technology was chosen")
    alternatives: List[str] = Field(default_factory=list, description="Alternative options considered")
    trade_offs: Dict[str, str] = Field(default_factory=dict, description="Trade-offs and considerations")


class SolutionArchitectOutput(AgentOutput):
    """Output from Solution Architect agent."""

    technology_stack: List[TechnologyChoice] = Field(..., description="Recommended technology stack")
    architecture_pattern: str = Field(..., description="Chosen architecture pattern")
    component_diagram: str = Field(..., description="Mermaid diagram of system components")
    data_flow_description: str = Field(..., description="Data flow and integration patterns")
    scalability_plan: str = Field(..., description="Scalability and performance considerations")
    security_considerations: List[str] = Field(..., description="Security requirements and measures")
    deployment_strategy: str = Field(..., description="Deployment and infrastructure strategy")
    technical_risks: List[str] = Field(..., description="Technical risks and mitigation strategies")

    model_config = {"extra": "forbid"}