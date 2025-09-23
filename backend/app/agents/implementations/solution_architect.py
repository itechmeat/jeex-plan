"""
Solution Architect Agent implementation.
Specializes in technical architecture, technology stack, and system design.
"""

import json
import re
from typing import Type, Dict, Any, List

from ..base.agent_base import AgentBase
from ..base.vector_context import vector_context
from ..base.quality_control import quality_controller
from ..contracts.base import (
    ProjectContext,
    AgentInput,
    AgentOutput,
    ValidationResult,
    ValidationError as AgentValidationError,
)
from ..contracts.solution_architect import (
    SolutionArchitectInput,
    SolutionArchitectOutput,
    TechnologyChoice,
)


class SolutionArchitectAgent(AgentBase):
    """Solution Architect specializing in technical architecture and system design."""

    def __init__(self) -> None:
        super().__init__(
            name="Solution Architect",
            role="Senior Solution Architect",
            goal=(
                "Design robust technical architectures with optimal technology stacks, "
                "scalable patterns, and clear component relationships"
            ),
            backstory="""You are a senior solution architect with 15+ years of experience
            designing scalable systems across various domains. You excel at choosing the right
            technologies, designing clean architectures, and balancing technical trade-offs
            while considering business requirements and team capabilities.""",
        )

    def get_input_model(self) -> Type[AgentInput]:
        return SolutionArchitectInput

    def get_output_model(self) -> Type[AgentOutput]:
        return SolutionArchitectOutput

    async def validate_input(self, input_data: SolutionArchitectInput) -> None:
        if (
            not input_data.project_description
            or len(input_data.project_description.strip()) < 50
        ):
            raise AgentValidationError(
                "Project description must be at least 50 characters for architecture analysis",
                agent_type="solution_architect",
                correlation_id=input_data.context.correlation_id,
                details={
                    "has_project_description": bool(input_data.project_description),
                    "description_length": (
                        len(input_data.project_description.strip())
                        if input_data.project_description else 0
                    ),
                    "minimum_required_length": 50,
                }
            )

    async def validate_output(
        self, output_data: SolutionArchitectOutput
    ) -> ValidationResult:
        correlation_id = output_data.metadata.get("correlation_id", "unknown")
        return await quality_controller.validate_agent_output(
            output_data,
            "solution_architect",
            correlation_id,
        )

    def get_system_prompt(self, context: ProjectContext) -> str:
        return f"""You are a Senior Solution Architect designing technical architectures
for projects.

**Document Language:** {context.language}

**Your Expertise:**
- Modern web architectures (microservices, serverless, monolithic)
- Technology stack selection and optimization
- Scalability and performance design
- Security architecture and best practices
- Cloud-native and container technologies
- API design and integration patterns

**Output Structure Expected:**
```markdown
# Technical Architecture

## Executive Summary
[High-level architecture overview and approach]

## Technology Stack
[Detailed technology choices with rationale]

## Architecture Pattern
[Selected pattern with justification]

## System Components
[Component breakdown with responsibilities]

## Component Diagram
[Mermaid diagram of system architecture]

## Data Flow & Integration
[Data flow patterns and external integrations]

## Scalability Strategy
[Performance and scaling considerations]

## Security Architecture
[Security measures and protocols]

## Deployment Strategy
[Infrastructure and deployment approach]

## Technical Risks & Mitigation
[Technical risks and solutions]
```

Focus on practical, implementable solutions that balance complexity with business needs."""

    async def get_context_data(self, context: ProjectContext) -> Dict[str, Any]:
        # Get business context from previous step
        return await vector_context.get_previous_steps_context(
            context, context.current_step
        )

    def _build_task_description(
        self, input_data: SolutionArchitectInput, context_data: Dict[str, Any]
    ) -> str:
        # NOTE: Task description uses basic template
        # Could be enhanced with context-aware prompts
        knowledge_facts = context_data.get('knowledge_facts', [])[:5]
        context_info = (
            json.dumps(knowledge_facts, indent=2)
            if knowledge_facts else 'No previous context available'
        )

        return f"""Design a comprehensive technical architecture for the following project:

**Project Description:**
{input_data.project_description}

**Additional Context:**
{context_info}

Create a detailed technical architecture document with technology recommendations,
component design, and scalability considerations."""

    def _get_expected_output_format(self) -> str:
        return (
            "A comprehensive technical architecture document including technology stack, "
            "component design, scalability strategy, and deployment approach."
        )

    def _parse_markdown_section(self, content: str, section_name: str) -> List[str]:
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
        lines = [line.strip() for line in section_content.split('\n')]
        paragraphs = [line for line in lines if line and not line.startswith(('-', '*', '+'))]

        return ' '.join(paragraphs) if paragraphs else ""

    def _parse_technology_stack(self, content: str) -> List[TechnologyChoice]:
        """Parse technology stack from markdown content."""
        tech_items = self._parse_markdown_section(content, "Technology Stack")
        technology_stack = []

        for item in tech_items:
            # Try to extract category and rationale if available
            category = "General"
            rationale = ""

            # Check if item contains category information (e.g., "Frontend: React - For UI")
            if ":" in item:
                parts = item.split(":", 1)
                if len(parts) == 2:
                    category = parts[0].strip()
                    item_desc = parts[1].strip()

                    # Check for rationale after dash
                    if " - " in item_desc:
                        tech_parts = item_desc.split(" - ", 1)
                        tech_name = tech_parts[0].strip()
                        rationale = tech_parts[1].strip()
                    else:
                        tech_name = item_desc
                else:
                    tech_name = item
            else:
                tech_name = item

            technology = TechnologyChoice(
                name=tech_name,
                category=category,
                rationale=rationale
            )
            technology_stack.append(technology)

        return technology_stack

    async def _parse_crew_result(
        self, result: Any, execution_time_ms: int
    ) -> SolutionArchitectOutput:
        content = str(result) if result is not None else ""

        # Parse structured fields from markdown content
        technology_stack = self._parse_technology_stack(content)

        architecture_pattern = (
            self._extract_text_section(content, "Architecture Pattern") or
            self._extract_text_section(content, "Architecture")
        )

        component_diagram = (
            self._extract_text_section(content, "Component Diagram") or
            self._extract_text_section(content, "Components")
        )

        data_flow_description = (
            self._extract_text_section(content, "Data Flow") or
            self._extract_text_section(content, "Data Flow & Integration")
        )

        scalability_plan = (
            self._extract_text_section(content, "Scalability Plan") or
            self._extract_text_section(content, "Scalability Strategy")
        )

        security_considerations = (
            self._parse_markdown_section(content, "Security Considerations") or
            self._parse_markdown_section(content, "Security Architecture")
        )

        deployment_strategy = (
            self._extract_text_section(content, "Deployment Strategy") or
            self._extract_text_section(content, "Deployment")
        )

        technical_risks = (
            self._parse_markdown_section(content, "Technical Risks") or
            self._parse_markdown_section(content, "Risks")
        )

        # Calculate confidence score based on populated sections
        populated_sections = sum([
            1 if technology_stack else 0,
            1 if architecture_pattern else 0,
            1 if component_diagram else 0,
            1 if data_flow_description else 0,
            1 if scalability_plan else 0,
            1 if security_considerations else 0,
            1 if deployment_strategy else 0,
            1 if technical_risks else 0,
        ])

        total_sections = 8
        if populated_sections > 0:
            confidence_score = min(0.95, populated_sections / total_sections)
        else:
            confidence_score = 0.0

        # Create validation result based on content quality
        validation_passed = populated_sections >= 4  # At least half sections populated
        validation_score = confidence_score

        missing_sections = []
        if not technology_stack:
            missing_sections.append("Technology Stack")
        if not architecture_pattern:
            missing_sections.append("Architecture Pattern")
        if not security_considerations:
            missing_sections.append("Security Considerations")

        suggestions = []
        if not component_diagram:
            suggestions.append("Add component diagram or architecture visualization")
        if not technical_risks:
            suggestions.append("Include technical risk assessment")

        return SolutionArchitectOutput(
            content=content,
            confidence_score=confidence_score,
            validation_result=ValidationResult(
                passed=validation_passed,
                score=validation_score,
                details={
                    "populated_sections": populated_sections,
                    "total_sections": total_sections,
                    "sections_found": {
                        "technology_stack": len(technology_stack),
                        "architecture_pattern": bool(architecture_pattern),
                        "component_diagram": bool(component_diagram),
                        "data_flow_description": bool(data_flow_description),
                        "scalability_plan": bool(scalability_plan),
                        "security_considerations": len(security_considerations),
                        "deployment_strategy": bool(deployment_strategy),
                        "technical_risks": len(technical_risks),
                    }
                },
                missing_sections=missing_sections,
                suggestions=suggestions
            ),
            metadata={
                "execution_time_ms": execution_time_ms,
                "agent_type": "solution_architect",
            },
            processing_time_ms=execution_time_ms,
            technology_stack=technology_stack,
            architecture_pattern=architecture_pattern,
            component_diagram=component_diagram,
            data_flow_description=data_flow_description,
            scalability_plan=scalability_plan,
            security_considerations=security_considerations,
            deployment_strategy=deployment_strategy,
            technical_risks=technical_risks,
        )
