"""
Workflow Engine for managing agent execution flows.
"""

from typing import Dict, Any, Optional
from enum import Enum

from ..contracts.base import ProjectContext
from ..contracts.business_analyst import BusinessAnalystInput
from ..contracts.solution_architect import SolutionArchitectInput
from ..contracts.project_planner import ProjectPlannerInput
from ..contracts.engineering_standards import EngineeringStandardsInput
from .orchestrator import WorkflowStep, orchestrator
from app.core.logger import get_logger

logger = get_logger()


class WorkflowEngine:
    """Manages workflow execution and step coordination."""

    def __init__(self):
        self.logger = get_logger("workflow_engine")

    async def execute_business_analysis(
        self,
        context: ProjectContext,
        idea_description: str,
        user_clarifications: Optional[Dict[str, Any]] = None,
        target_audience: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute business analysis step."""
        input_data = BusinessAnalystInput(
            context=context,
            idea_description=idea_description,
            user_clarifications=user_clarifications,
            target_audience=target_audience,
        )

        result = await orchestrator.execute_step(
            WorkflowStep.BUSINESS_ANALYSIS, context, input_data
        )

        return {
            "status": result.status,
            "content": result.output_data.content if result.output_data else None,
            "confidence_score": (
                result.output_data.confidence_score if result.output_data else 0.0
            ),
            "validation_result": (
                result.output_data.validation_result.model_dump()
                if result.output_data
                else None
            ),
            "execution_time_ms": result.execution_time_ms,
            "error_message": result.error_message,
        }

    async def execute_architecture_design(
        self,
        context: ProjectContext,
        project_description: str,
        user_tech_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute architecture design step."""
        input_data = SolutionArchitectInput(
            context=context,
            project_description=project_description,
            user_tech_preferences=user_tech_preferences,
        )

        result = await orchestrator.execute_step(
            WorkflowStep.ARCHITECTURE_DESIGN, context, input_data
        )

        return {
            "status": result.status,
            "content": result.output_data.content if result.output_data else None,
            "confidence_score": (
                result.output_data.confidence_score if result.output_data else 0.0
            ),
            "validation_result": (
                result.output_data.validation_result.model_dump()
                if result.output_data
                else None
            ),
            "execution_time_ms": result.execution_time_ms,
            "error_message": result.error_message,
        }

    async def execute_implementation_planning(
        self,
        context: ProjectContext,
        project_description: str,
        architecture_overview: str,
        team_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute implementation planning step."""
        input_data = ProjectPlannerInput(
            context=context,
            project_description=project_description,
            architecture_overview=architecture_overview,
            team_size=team_size,
        )

        result = await orchestrator.execute_step(
            WorkflowStep.IMPLEMENTATION_PLANNING, context, input_data
        )

        return {
            "status": result.status,
            "content": result.output_data.content if result.output_data else None,
            "confidence_score": (
                result.output_data.confidence_score if result.output_data else 0.0
            ),
            "validation_result": (
                result.output_data.validation_result.model_dump()
                if result.output_data
                else None
            ),
            "execution_time_ms": result.execution_time_ms,
            "error_message": result.error_message,
        }

    async def execute_engineering_standards(
        self,
        context: ProjectContext,
        project_description: str,
        technology_stack: list[str],
        team_experience_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute engineering standards step."""
        input_data = EngineeringStandardsInput(
            context=context,
            project_description=project_description,
            technology_stack=technology_stack,
            team_experience_level=team_experience_level,
        )

        result = await orchestrator.execute_step(
            WorkflowStep.ENGINEERING_STANDARDS, context, input_data
        )

        return {
            "status": result.status,
            "content": result.output_data.content if result.output_data else None,
            "confidence_score": (
                result.output_data.confidence_score if result.output_data else 0.0
            ),
            "validation_result": (
                result.output_data.validation_result.model_dump()
                if result.output_data
                else None
            ),
            "execution_time_ms": result.execution_time_ms,
            "error_message": result.error_message,
        }


# Global workflow engine instance
workflow_engine = WorkflowEngine()
