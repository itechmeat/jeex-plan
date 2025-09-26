"""
Agent system package for JEEX Plan.
Multi-agent orchestration with CrewAI and Pydantic AI contracts.
"""

from .contracts.base import AgentInput, AgentOutput, ProjectContext
from .contracts.business_analyst import BusinessAnalystInput, BusinessAnalystOutput
from .contracts.engineering_standards import (
    EngineeringStandardsInput,
    EngineeringStandardsOutput,
)
from .contracts.project_planner import ProjectPlannerInput, ProjectPlannerOutput
from .contracts.solution_architect import (
    SolutionArchitectInput,
    SolutionArchitectOutput,
)

__all__ = [
    "AgentInput",
    "AgentOutput",
    "BusinessAnalystInput",
    "BusinessAnalystOutput",
    "EngineeringStandardsInput",
    "EngineeringStandardsOutput",
    "ProjectContext",
    "ProjectPlannerInput",
    "ProjectPlannerOutput",
    "SolutionArchitectInput",
    "SolutionArchitectOutput",
]
