"""
Project Planner agent contracts.
Handles implementation planning, task breakdown, and project roadmap.
"""

from pydantic import BaseModel, Field

from .base import AgentInput, AgentOutput


class Epic(BaseModel):
    """Epic definition with tasks and acceptance criteria."""

    id: str = Field(..., description="Epic identifier (e.g., '01-infrastructure')")
    title: str = Field(..., description="Epic title")
    description: str = Field(..., description="Epic description and objectives")
    tasks: list[str] = Field(..., description="List of tasks within the epic")
    acceptance_criteria: list[str] = Field(..., description="Epic acceptance criteria")
    dependencies: list[str] = Field(
        default_factory=list, description="Dependencies on other epics"
    )
    estimated_effort: str = Field(..., description="Effort estimation (weeks/sprints)")
    risks: list[str] = Field(default_factory=list, description="Epic-specific risks")


class ProjectPlannerInput(AgentInput):
    """Input data for Project Planner agent."""

    project_description: str = Field(..., description="Complete project description")
    engineering_standards: str = Field(
        ..., description="Engineering standards and specifications"
    )
    architecture_overview: str = Field(
        ..., description="Technical architecture from Solution Architect"
    )
    team_size: int | None = Field(None, description="Development team size")
    timeline_constraints: str | None = Field(None, description="Timeline requirements")
    priority_features: list[str] | None = Field(
        None, description="High-priority features"
    )
    mvp_requirements: str | None = Field(None, description="MVP scope definition")

    model_config = {"extra": "forbid"}


class ProjectPlannerOutput(AgentOutput):
    """Output from Project Planner agent."""

    overview_strategy: str = Field(
        ..., description="High-level implementation strategy"
    )
    epics: list[Epic] = Field(..., description="List of implementation epics")
    timeline_estimate: str = Field(..., description="Overall timeline estimation")
    critical_path: list[str] = Field(
        ..., description="Critical path items and bottlenecks"
    )
    milestone_schedule: dict[str, str] = Field(
        ..., description="Key milestones and dates"
    )
    resource_requirements: list[str] = Field(
        ..., description="Required resources and skills"
    )
    quality_gates: list[str] = Field(..., description="Quality checkpoints and reviews")
    project_risks: list[str] = Field(
        ..., description="Project-level risks and contingencies"
    )

    model_config = {"extra": "forbid"}
