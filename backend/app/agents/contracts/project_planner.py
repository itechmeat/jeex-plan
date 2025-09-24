"""
Project Planner agent contracts.
Handles implementation planning, task breakdown, and project roadmap.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from .base import AgentInput, AgentOutput


class Epic(BaseModel):
    """Epic definition with tasks and acceptance criteria."""

    id: str = Field(..., description="Epic identifier (e.g., '01-infrastructure')")
    title: str = Field(..., description="Epic title")
    description: str = Field(..., description="Epic description and objectives")
    tasks: List[str] = Field(..., description="List of tasks within the epic")
    acceptance_criteria: List[str] = Field(..., description="Epic acceptance criteria")
    dependencies: List[str] = Field(
        default_factory=list, description="Dependencies on other epics"
    )
    estimated_effort: str = Field(..., description="Effort estimation (weeks/sprints)")
    risks: List[str] = Field(default_factory=list, description="Epic-specific risks")


class ProjectPlannerInput(AgentInput):
    """Input data for Project Planner agent."""

    project_description: str = Field(..., description="Complete project description")
    engineering_standards: str = Field(
        ..., description="Engineering standards and specifications"
    )
    architecture_overview: str = Field(
        ..., description="Technical architecture from Solution Architect"
    )
    team_size: Optional[int] = Field(None, description="Development team size")
    timeline_constraints: Optional[str] = Field(
        None, description="Timeline requirements"
    )
    priority_features: Optional[List[str]] = Field(
        None, description="High-priority features"
    )
    mvp_requirements: Optional[str] = Field(None, description="MVP scope definition")

    model_config = {"extra": "forbid"}


class ProjectPlannerOutput(AgentOutput):
    """Output from Project Planner agent."""

    overview_strategy: str = Field(
        ..., description="High-level implementation strategy"
    )
    epics: List[Epic] = Field(..., description="List of implementation epics")
    timeline_estimate: str = Field(..., description="Overall timeline estimation")
    critical_path: List[str] = Field(
        ..., description="Critical path items and bottlenecks"
    )
    milestone_schedule: Dict[str, str] = Field(
        ..., description="Key milestones and dates"
    )
    resource_requirements: List[str] = Field(
        ..., description="Required resources and skills"
    )
    quality_gates: List[str] = Field(..., description="Quality checkpoints and reviews")
    project_risks: List[str] = Field(
        ..., description="Project-level risks and contingencies"
    )

    model_config = {"extra": "forbid"}
