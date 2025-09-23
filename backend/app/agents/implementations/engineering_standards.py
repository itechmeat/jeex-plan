"""
Engineering Standards Agent implementation.
Handles code quality standards, review processes, and technical guidelines.
"""

from typing import Type, Dict, Any, List

from ..base.agent_base import AgentBase
from ..base.vector_context import vector_context
from ..base.quality_control import quality_controller
from ..contracts.base import ProjectContext, AgentInput, AgentOutput, ValidationResult
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
            goal="Establish comprehensive engineering standards, code quality guidelines, and development best practices",
            backstory="""You are a senior software engineer with deep expertise in code quality, testing strategies,
            and development best practices across multiple technology stacks. You focus on creating practical,
            enforceable standards that improve code quality without hindering productivity.""",
        )

    def get_input_model(self) -> Type[AgentInput]:
        return EngineeringStandardsInput

    def get_output_model(self) -> Type[AgentOutput]:
        return EngineeringStandardsOutput

    async def validate_input(self, input_data: EngineeringStandardsInput) -> None:
        if not input_data.project_description or not input_data.technology_stack:
            raise ValueError(
                "Project description and technology stack are required for standards generation"
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
        return f"""You are a Senior Software Engineer establishing development standards for a technical project.

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
        # NOTE: Task description uses basic template - could be enhanced with technology-specific prompts
        tech_stack_str = ", ".join(input_data.technology_stack)
        return f"""Create comprehensive engineering standards for this project:

**Technology Stack:** {tech_stack_str}
**Project Context:** {input_data.project_description[:400]}...

Establish practical standards covering code quality, testing, security, and development processes.
Focus on standards that can be automated and enforced through tooling."""

    def _get_expected_output_format(self) -> str:
        return """Complete engineering standards document with code guidelines, testing strategy, and quality processes."""

    async def _parse_crew_result(
        self, result: Any, execution_time_ms: int
    ) -> EngineeringStandardsOutput:
        content = str(result)

        # NOTE: Structured parsing not yet implemented - returns basic output with empty structured fields
        return EngineeringStandardsOutput(
            content=content,
            confidence_score=0.0,
            validation_result=ValidationResult(
                passed=False, score=0.0, details={}, missing_sections=[], suggestions=[]
            ),
            metadata={
                "execution_time_ms": execution_time_ms,
                "agent_type": "engineering_standards",
            },
            processing_time_ms=execution_time_ms,
            coding_standards=[],  # NOTE: Standards parsing not implemented
            review_process="",  # NOTE: Review process extraction not implemented
            definition_of_done=[],  # NOTE: DoD extraction not implemented
            testing_strategy="",  # NOTE: Testing strategy extraction not implemented
            security_guidelines=[],  # NOTE: Security extraction not implemented
            performance_standards=[],  # NOTE: Performance extraction not implemented
            documentation_requirements=[],  # NOTE: Documentation extraction not implemented
            toolchain_recommendations={},  # NOTE: Toolchain extraction not implemented
        )
