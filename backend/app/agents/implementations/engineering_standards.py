"""
Engineering Standards Agent implementation.
Handles code quality standards, review processes, and technical guidelines.
"""

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
from ..contracts.engineering_standards import (
    EngineeringStandardsInput,
    EngineeringStandardsOutput,
    CodeStandard,
)


class EngineeringStandardsAgent(AgentBase):
    """Engineering Standards specialist for code quality and best practices."""

    def __init__(self) -> None:
        super().__init__(
            name="Engineering Standards",
            role="Senior Software Engineer & Quality Lead",
            goal=(
                "Establish comprehensive engineering standards, code quality "
                "guidelines, and development best practices"
            ),
            backstory="""You are a senior software engineer with deep expertise in code quality,
            testing strategies, and development best practices across multiple technology stacks.
            You focus on creating practical, enforceable standards that improve code quality
            without hindering productivity.""",
        )

    def get_input_model(self) -> Type[AgentInput]:
        return EngineeringStandardsInput

    def get_output_model(self) -> Type[AgentOutput]:
        return EngineeringStandardsOutput

    async def validate_input(self, input_data: EngineeringStandardsInput) -> None:
        if not input_data.project_description or not input_data.technology_stack:
            raise AgentValidationError(
                (
                    "Project description and technology stack are required "
                    "for standards generation"
                ),
                agent_type="engineering_standards",
                correlation_id=input_data.context.correlation_id,
                details={
                    "has_project_description": bool(input_data.project_description),
                    "has_technology_stack": bool(input_data.technology_stack),
                }
            )

    async def validate_output(
        self, output_data: EngineeringStandardsOutput
    ) -> ValidationResult:
        return await quality_controller.validate_agent_output(
            output_data,
            "engineering_standards",
            output_data.metadata.get("correlation_id", "unknown"),
        )

    def get_system_prompt(self, context: ProjectContext) -> str:
        return f"""You are a Senior Software Engineer establishing development standards
for a technical project.

**Document Language:** {context.language}

**Your Focus Areas:**
- Code quality standards and style guides
- Code review processes and checklists
- Testing strategies and coverage requirements
- Security guidelines and best practices
- Documentation standards
- Definition of Done criteria
- Tool recommendations and automation

**Output Structure:**
```markdown
# Engineering Standards & Guidelines

## Code Quality Standards
[Language-specific coding guidelines]

## Code Review Process
[Review workflow and checklist]

## Definition of Done
[Completion criteria for features]

## Testing Strategy
[Testing approach and requirements]

## Security Guidelines
[Security best practices and requirements]

## Performance Standards
[Performance requirements and monitoring]

## Documentation Requirements
[Documentation standards and expectations]

## Recommended Toolchain
[Development tools and automation]

## Quality Assurance Process
[QA workflow and checkpoints]
```

Create practical, enforceable standards that improve quality without hindering productivity."""

    async def get_context_data(self, context: ProjectContext) -> Dict[str, Any]:
        return await vector_context.get_previous_steps_context(
            context, context.current_step
        )

    def _build_task_description(
        self, input_data: EngineeringStandardsInput, context_data: Dict[str, Any]
    ) -> str:
        # NOTE: Task description uses basic template
        # Could be enhanced with technology-specific prompts
        tech_stack_str = ", ".join(input_data.technology_stack)
        description_preview = input_data.project_description[:400]
        return f"""Create comprehensive engineering standards for this project:

**Technology Stack:** {tech_stack_str}
**Project Context:** {description_preview}...

Create practical, enforceable standards covering code quality, testing, security,
and development processes.
Focus on standards that can be automated and enforced through tooling."""

    def _get_expected_output_format(self) -> str:
        return (
            "Complete engineering standards document with code guidelines, "
            "testing strategy, and quality processes."
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

    def _parse_code_standards(self, content: str) -> List[CodeStandard]:
        """Parse code quality standards section into CodeStandard objects."""
        standards_bullets = self._parse_markdown_section(content, "Code Quality Standards")
        code_standards = []

        for bullet in standards_bullets:
            # Create basic CodeStandard from bullet text
            standard = CodeStandard(
                category="General",
                rules=[bullet],
                examples=None,
                tools=[]
            )
            code_standards.append(standard)

        return code_standards

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

    def _parse_toolchain_recommendations(self, content: str) -> Dict[str, List[str]]:
        """Parse toolchain recommendations into categorized dictionary."""
        tools_bullets = self._parse_markdown_section(content, "Recommended Toolchain")
        toolchain = {}

        current_category = "General"
        for bullet in tools_bullets:
            # Check if bullet contains a category (ends with colon)
            if bullet.endswith(':'):
                current_category = bullet[:-1].strip()
                toolchain[current_category] = []
            else:
                if current_category not in toolchain:
                    toolchain[current_category] = []
                toolchain[current_category].append(bullet)

        return toolchain

    async def _parse_crew_result(
        self, result: Any, execution_time_ms: int
    ) -> EngineeringStandardsOutput:
        content = str(result)

        # Parse structured fields from markdown content
        coding_standards = self._parse_code_standards(content)
        review_process = self._extract_text_section(content, "Code Review Process")
        definition_of_done = self._parse_markdown_section(content, "Definition of Done")
        testing_strategy = self._extract_text_section(content, "Testing Strategy")
        security_guidelines = self._parse_markdown_section(content, "Security Guidelines")
        performance_standards = self._parse_markdown_section(content, "Performance Standards")
        documentation_requirements = self._parse_markdown_section(
            content, "Documentation Requirements"
        )
        toolchain_recommendations = self._parse_toolchain_recommendations(content)

        # Calculate confidence score based on populated sections
        populated_sections = sum([
            1 if coding_standards else 0,
            1 if review_process else 0,
            1 if definition_of_done else 0,
            1 if testing_strategy else 0,
            1 if security_guidelines else 0,
            1 if performance_standards else 0,
            1 if documentation_requirements else 0,
            1 if toolchain_recommendations else 0,
        ])

        total_sections = 8
        confidence_score = min(0.95, populated_sections / total_sections)

        # Create validation result based on content quality
        validation_passed = populated_sections >= 4  # At least half sections populated
        validation_score = confidence_score

        missing_sections = []
        if not coding_standards:
            missing_sections.append("Code Quality Standards")
        if not definition_of_done:
            missing_sections.append("Definition of Done")
        if not security_guidelines:
            missing_sections.append("Security Guidelines")

        suggestions = []
        if not review_process:
            suggestions.append("Add detailed code review process guidelines")
        if not testing_strategy:
            suggestions.append("Include comprehensive testing strategy")

        return EngineeringStandardsOutput(
            content=content,
            confidence_score=confidence_score,
            validation_result=ValidationResult(
                passed=validation_passed,
                score=validation_score,
                details={
                    "populated_sections": populated_sections,
                    "total_sections": total_sections,
                    "sections_found": {
                        "coding_standards": len(coding_standards),
                        "review_process": bool(review_process),
                        "definition_of_done": len(definition_of_done),
                        "testing_strategy": bool(testing_strategy),
                        "security_guidelines": len(security_guidelines),
                        "performance_standards": len(performance_standards),
                        "documentation_requirements": len(documentation_requirements),
                        "toolchain_recommendations": len(toolchain_recommendations),
                    }
                },
                missing_sections=missing_sections,
                suggestions=suggestions
            ),
            metadata={
                "execution_time_ms": execution_time_ms,
                "agent_type": "engineering_standards",
            },
            processing_time_ms=execution_time_ms,
            coding_standards=coding_standards,
            review_process=review_process,
            definition_of_done=definition_of_done,
            testing_strategy=testing_strategy,
            security_guidelines=security_guidelines,
            performance_standards=performance_standards,
            documentation_requirements=documentation_requirements,
            toolchain_recommendations=toolchain_recommendations,
        )
