"""
Agent system package for JEEX Plan.
Multi-agent orchestration with CrewAI and Pydantic AI contracts.
"""

from .contracts.base import ProjectContext, AgentInput, AgentOutput
from .contracts.business_analyst import BusinessAnalystInput, BusinessAnalystOutput
from .contracts.solution_architect import SolutionArchitectInput, SolutionArchitectOutput
from .contracts.project_planner import ProjectPlannerInput, ProjectPlannerOutput
from .contracts.engineering_standards import EngineeringStandardsInput, EngineeringStandardsOutput

__all__ = [
    "ProjectContext",
    "AgentInput",
    "AgentOutput",
    "BusinessAnalystInput",
    "BusinessAnalystOutput",
    "SolutionArchitectInput",
    "SolutionArchitectOutput",
    "ProjectPlannerInput",
    "ProjectPlannerOutput",
    "EngineeringStandardsInput",
    "EngineeringStandardsOutput",
]