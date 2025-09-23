"""
Project Planner Agent implementation.
Handles implementation planning, task breakdown, and project roadmap.
"""

from typing import Type, Dict, Any

from ..base.agent_base import AgentBase
from ..base.vector_context import vector_context
from ..base.quality_control import quality_controller
from ..contracts.base import ProjectContext, AgentInput, AgentOutput, ValidationResult
from ..contracts.project_planner import ProjectPlannerInput, ProjectPlannerOutput, Epic


class ProjectPlannerAgent(AgentBase):
    """Project Planner specializing in implementation planning and roadmaps."""

    def __init__(self):
        super().__init__(
            name="Project Planner",
            role="Senior Project Manager & Technical Lead",
            goal="Create detailed implementation plans with realistic timelines, clear epics, and risk-aware project roadmaps",
            backstory="""You are an experienced project manager and technical lead with expertise in Agile methodologies,
            technical project planning, and risk management. You excel at breaking down complex projects into
            manageable epics and sprints while considering team capabilities and technical dependencies.""",
        )

    def get_input_model(self) -> Type[AgentInput]:
        return ProjectPlannerInput

    def get_output_model(self) -> Type[AgentOutput]:
        return ProjectPlannerOutput

    async def validate_input(self, input_data: ProjectPlannerInput) -> None:
        if not input_data.project_description or len(input_data.project_description.strip()) < 50:
            raise ValueError("Project description must be substantial for planning")

    async def validate_output(self, output_data: ProjectPlannerOutput) -> ValidationResult:
        return await quality_controller.validate_agent_output(
            output_data, "project_planner", output_data.metadata.get("correlation_id", "unknown")
        )

    def get_system_prompt(self, context: ProjectContext) -> str:
        return f"""You are a Senior Project Manager creating implementation plans for technical projects.

**Document Language:** {context.language}

**Planning Philosophy:**
- Epic-based incremental development
- Always start with Epic 01 (Infrastructure) - minimal architecture setup
- End with final Epic (Testing & QA) - comprehensive testing
- Each epic should deliver working functionality
- Consider dependencies and team capabilities

**Epic Structure Pattern:**
1. **Epic 01 - Infrastructure**: Basic architecture setup with minimal functionality
2. **Epic 02-N**: Feature development epics (variable based on project scope)
3. **Epic N - Testing**: Comprehensive testing, performance, security audit

**Output Structure:**
```markdown
# Implementation Plan

## Project Overview
[High-level strategy and approach]

## Timeline & Milestones
[Overall timeline with key milestones]

## Epic Breakdown
[Detailed epic descriptions with tasks and acceptance criteria]

## Critical Path Analysis
[Dependencies and bottlenecks]

## Resource Requirements
[Team skills and resource needs]

## Risk Management
[Project risks and mitigation strategies]

## Quality Gates
[Review points and quality checkpoints]
```

Create practical, actionable plans that teams can execute successfully."""

    async def get_context_data(self, context: ProjectContext) -> Dict[str, Any]:
        return await vector_context.get_previous_steps_context(context, context.current_step)

    def _build_task_description(self, input_data: ProjectPlannerInput, context_data: Dict[str, Any]) -> str:
        # NOTE: Task description uses basic template - could be enhanced with context-aware prompts
        return f"""Create a detailed implementation plan for this project:

**Project:** {input_data.project_description[:500]}...
**Architecture:** {input_data.architecture_overview[:300] if input_data.architecture_overview else 'Architecture pending'}

Break down into epics following the pattern: Infrastructure → Features → Testing.
Include realistic timelines, dependencies, and risk assessment."""

    def _get_expected_output_format(self) -> str:
        return """A comprehensive implementation plan with epic breakdown, timeline estimates, and risk analysis."""

    async def _parse_crew_result(self, result: Any, execution_time_ms: int) -> ProjectPlannerOutput:
        content = str(result)

        # NOTE: Structured parsing not yet implemented - returns basic output with empty structured fields
        return ProjectPlannerOutput(
            content=content,
            confidence_score=0.0,
            validation_result=ValidationResult(passed=False, score=0.0, details={}, missing_sections=[], suggestions=[]),
            metadata={"execution_time_ms": execution_time_ms, "agent_type": "project_planner"},
            processing_time_ms=execution_time_ms,
            overview_strategy="",  # NOTE: Strategy extraction not implemented
            epics=[],  # NOTE: Epic parsing not implemented
            timeline_estimate="",  # NOTE: Timeline extraction not implemented
            critical_path=[],  # NOTE: Critical path extraction not implemented
            milestone_schedule={},  # NOTE: Milestone extraction not implemented
            resource_requirements=[],  # NOTE: Resource extraction not implemented
            quality_gates=[],  # NOTE: Quality gate extraction not implemented
            project_risks=[],  # NOTE: Risk extraction not implemented
        )