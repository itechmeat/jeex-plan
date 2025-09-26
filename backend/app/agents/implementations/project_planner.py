"""
Project Planner Agent implementation.
Handles implementation planning, task breakdown, and project roadmap.
"""

import re
from typing import Any

from ..base.agent_base import AgentBase
from ..base.quality_control import quality_controller
from ..base.vector_context import vector_context
from ..contracts.base import (
    AgentInput,
    AgentOutput,
    ProjectContext,
    ValidationResult,
)
from ..contracts.base import (
    ValidationError as AgentValidationError,
)
from ..contracts.project_planner import Epic, ProjectPlannerInput, ProjectPlannerOutput


class ProjectPlannerAgent(AgentBase):
    """Project Planner specializing in implementation planning and roadmaps."""

    def __init__(self) -> None:
        super().__init__(
            name="Project Planner",
            role="Senior Project Manager & Technical Lead",
            goal=(
                "Create detailed implementation plans with realistic timelines, "
                "clear epics, and risk-aware project roadmaps"
            ),
            backstory="""You are an experienced project manager and technical lead with expertise
            in Agile methodologies, technical project planning, and risk management.
            You excel at breaking down complex projects into manageable epics and sprints
            while considering team capabilities and technical dependencies.""",
        )

    def get_input_model(self) -> type[AgentInput]:
        return ProjectPlannerInput

    def get_output_model(self) -> type[AgentOutput]:
        return ProjectPlannerOutput

    async def validate_input(self, input_data: ProjectPlannerInput) -> None:
        if (
            not input_data.project_description
            or len(input_data.project_description.strip()) < 50
        ):
            raise AgentValidationError(
                "Project description must be substantial for planning",
                agent_type="project_planner",
                correlation_id=input_data.context.correlation_id,
                details={
                    "has_project_description": bool(input_data.project_description),
                    "description_length": (
                        len(input_data.project_description.strip())
                        if input_data.project_description
                        else 0
                    ),
                    "minimum_required_length": 50,
                },
            )

    async def validate_output(
        self, output_data: ProjectPlannerOutput
    ) -> ValidationResult:
        return await quality_controller.validate_agent_output(
            output_data,
            "project_planner",
            output_data.metadata.get("correlation_id", "unknown"),
        )

    def get_system_prompt(self, context: ProjectContext) -> str:
        return f"""You are a Senior Project Manager creating implementation plans
for technical projects.

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

    async def get_context_data(self, context: ProjectContext) -> dict[str, Any]:
        return await vector_context.get_previous_steps_context(
            context, context.current_step
        )

    def _build_task_description(
        self, input_data: ProjectPlannerInput, context_data: dict[str, Any]
    ) -> str:
        # NOTE: Task description uses basic template
        # Could be enhanced with context-aware prompts
        project_preview = input_data.project_description[:500]
        architecture_text = (
            input_data.architecture_overview[:300]
            if input_data.architecture_overview
            else "Architecture pending"
        )

        return f"""Create a detailed implementation plan for this project:

**Project:** {project_preview}...
**Architecture:** {architecture_text}

Break down into epics following the pattern: Infrastructure → Features → Testing.
Include realistic timelines, dependencies, and risk assessment."""

    def _get_expected_output_format(self) -> str:
        return (
            "A comprehensive implementation plan with epic breakdown, "
            "timeline estimates, and risk analysis."
        )

    def _parse_markdown_section(self, content: str, section_name: str) -> list[str]:
        """Extract bullet point items from a specific markdown section."""
        pattern = rf"#{1,2}\s+{re.escape(section_name)}.*?\n(.*?)(?=#{1,2}|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if not match:
            return []

        section_content = match.group(1)
        # Extract bullet points (lines starting with -, *, or +)
        bullet_pattern = r"^[\s]*[-\*\+]\s+(.+)$"
        bullets = re.findall(bullet_pattern, section_content, re.MULTILINE)

        return [bullet.strip() for bullet in bullets if bullet.strip()]

    def _extract_text_section(self, content: str, section_name: str) -> str:
        """Extract text content from a markdown section (non-bullet format)."""
        pattern = rf"#{1,2}\s+{re.escape(section_name)}.*?\n(.*?)(?=#{1,2}|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if not match:
            return ""

        section_content = match.group(1).strip()
        # Remove bullet points and keep paragraph text
        lines = [line.strip() for line in section_content.split("\n")]
        paragraphs = [
            line for line in lines if line and not line.startswith(("-", "*", "+"))
        ]

        return " ".join(paragraphs) if paragraphs else ""

    def _parse_epics_section(self, content: str) -> list[Epic]:
        """Parse epics from markdown content."""
        epics = []

        # Look for Epic sections
        epic_pattern = r"#{2,3}\s+(Epic\s+\d+[^\n]*)\n(.*?)(?=#{2,3}\s+Epic|\Z)"
        epic_matches = re.findall(epic_pattern, content, re.DOTALL | re.IGNORECASE)

        for title, epic_content in epic_matches:
            # Extract epic ID from title (e.g., "Epic 01" -> "01")
            epic_id_match = re.search(r"Epic\s+(\d+)", title, re.IGNORECASE)
            epic_id = (
                epic_id_match.group(1) if epic_id_match else f"epic_{len(epics) + 1}"
            )

            # Parse tasks from the epic content
            tasks = self._parse_markdown_section(epic_content, "Tasks")
            if not tasks:
                # Try alternative patterns for tasks
                task_bullets = re.findall(
                    r"^[\s]*[-\*\+]\s+(.+)$", epic_content, re.MULTILINE
                )
                tasks = [task.strip() for task in task_bullets if task.strip()]

            # Parse acceptance criteria
            acceptance_criteria = self._parse_markdown_section(
                epic_content, "Acceptance Criteria"
            )

            # Extract estimated effort
            effort_match = re.search(
                r"Effort[:\s]*([^\n]+)", epic_content, re.IGNORECASE
            )
            estimated_effort = effort_match.group(1).strip() if effort_match else "TBD"

            epic = Epic(
                id=f"{epic_id.zfill(2)}-{title.lower().replace(' ', '-')}",
                title=title,
                description=epic_content[:200] + "..."
                if len(epic_content) > 200
                else epic_content,
                tasks=tasks[:10],  # Limit to first 10 tasks
                acceptance_criteria=acceptance_criteria,
                dependencies=[],
                estimated_effort=estimated_effort,
                risks=[],
            )
            epics.append(epic)

        return epics

    def _parse_milestones(self, content: str) -> dict[str, str]:
        """Parse milestones into a dictionary."""
        milestones = {}
        milestone_bullets = self._parse_markdown_section(content, "Milestones")

        for bullet in milestone_bullets:
            # Try to extract milestone name and date/duration
            milestone_match = re.match(r"(.+?)[:–-](.+)", bullet)
            if milestone_match:
                name = milestone_match.group(1).strip()
                date = milestone_match.group(2).strip()
                milestones[name] = date
            else:
                milestones[bullet] = "TBD"

        return milestones

    async def _parse_crew_result(
        self, result: object, execution_time_ms: int
    ) -> ProjectPlannerOutput:
        content = str(result)

        # Parse structured fields from markdown content
        overview_strategy = (
            self._extract_text_section(content, "Overview")
            or self._extract_text_section(content, "Strategy")
            or self._extract_text_section(content, "Implementation Strategy")
        )

        epics = self._parse_epics_section(content)

        timeline_estimate = self._extract_text_section(
            content, "Timeline"
        ) or self._extract_text_section(content, "Timeline Estimate")

        critical_path = self._parse_markdown_section(content, "Critical Path")

        milestone_schedule = self._parse_milestones(content)

        resource_requirements = self._parse_markdown_section(
            content, "Resource Requirements"
        ) or self._parse_markdown_section(content, "Resources")

        quality_gates = self._parse_markdown_section(
            content, "Quality Gates"
        ) or self._parse_markdown_section(content, "Quality Checkpoints")

        project_risks = self._parse_markdown_section(
            content, "Risks"
        ) or self._parse_markdown_section(content, "Project Risks")

        # Calculate confidence score based on populated sections
        populated_sections = sum(
            [
                1 if overview_strategy else 0,
                1 if epics else 0,
                1 if timeline_estimate else 0,
                1 if critical_path else 0,
                1 if milestone_schedule else 0,
                1 if resource_requirements else 0,
                1 if quality_gates else 0,
                1 if project_risks else 0,
            ]
        )

        total_sections = 8
        confidence_score = min(0.95, populated_sections / total_sections)

        # Create validation result based on content quality
        validation_passed = populated_sections >= 4  # At least half sections populated
        validation_score = confidence_score

        missing_sections = []
        if not overview_strategy:
            missing_sections.append("Overview/Strategy")
        if not epics:
            missing_sections.append("Epics")
        if not timeline_estimate:
            missing_sections.append("Timeline Estimate")

        suggestions = []
        if not critical_path:
            suggestions.append("Add critical path analysis")
        if not project_risks:
            suggestions.append("Include project risk assessment")

        return ProjectPlannerOutput(
            content=content,
            confidence_score=confidence_score,
            validation_result=ValidationResult(
                passed=validation_passed,
                score=validation_score,
                details={
                    "populated_sections": populated_sections,
                    "total_sections": total_sections,
                    "sections_found": {
                        "overview_strategy": bool(overview_strategy),
                        "epics": len(epics),
                        "timeline_estimate": bool(timeline_estimate),
                        "critical_path": len(critical_path),
                        "milestone_schedule": len(milestone_schedule),
                        "resource_requirements": len(resource_requirements),
                        "quality_gates": len(quality_gates),
                        "project_risks": len(project_risks),
                    },
                },
                missing_sections=missing_sections,
                suggestions=suggestions,
            ),
            metadata={
                "execution_time_ms": execution_time_ms,
                "agent_type": "project_planner",
            },
            processing_time_ms=execution_time_ms,
            overview_strategy=overview_strategy,
            epics=epics,
            timeline_estimate=timeline_estimate,
            critical_path=critical_path,
            milestone_schedule=milestone_schedule,
            resource_requirements=resource_requirements,
            quality_gates=quality_gates,
            project_risks=project_risks,
        )
