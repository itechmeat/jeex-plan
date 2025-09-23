"""
Solution Architect Agent implementation.
Specializes in technical architecture, technology stack, and system design.
"""

import json
from typing import Type, Dict, Any

from ..base.agent_base import AgentBase
from ..base.vector_context import vector_context
from ..base.quality_control import quality_controller
from ..contracts.base import ProjectContext, AgentInput, AgentOutput, ValidationResult
from ..contracts.solution_architect import SolutionArchitectInput, SolutionArchitectOutput, TechnologyChoice


class SolutionArchitectAgent(AgentBase):
    """Solution Architect specializing in technical architecture and system design."""

    def __init__(self):
        super().__init__(
            name="Solution Architect",
            role="Senior Solution Architect",
            goal="Design robust technical architectures with optimal technology stacks, scalable patterns, and clear component relationships",
            backstory="""You are a senior solution architect with 15+ years of experience designing scalable systems
            across various domains. You excel at choosing the right technologies, designing clean architectures,
            and balancing technical trade-offs while considering business requirements and team capabilities.""",
        )

    def get_input_model(self) -> Type[AgentInput]:
        return SolutionArchitectInput

    def get_output_model(self) -> Type[AgentOutput]:
        return SolutionArchitectOutput

    async def validate_input(self, input_data: SolutionArchitectInput) -> None:
        if not input_data.project_description or len(input_data.project_description.strip()) < 50:
            raise ValueError("Project description must be at least 50 characters for architecture analysis")

    async def validate_output(self, output_data: SolutionArchitectOutput) -> ValidationResult:
        return await quality_controller.validate_agent_output(
            output_data, "solution_architect", output_data.metadata.get("correlation_id", "unknown")
        )

    def get_system_prompt(self, context: ProjectContext) -> str:
        return f"""You are a Senior Solution Architect designing technical architectures for projects.

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
        return await vector_context.get_previous_steps_context(context, context.current_step)

    def _build_task_description(self, input_data: SolutionArchitectInput, context_data: Dict[str, Any]) -> str:
        # NOTE: Task description uses basic template - could be enhanced with context-aware prompts
        return f"""Design a comprehensive technical architecture for the following project:

**Project Description:**
{input_data.project_description}

**Additional Context:**
{json.dumps(context_data.get('knowledge_facts', [])[:5], indent=2) if context_data.get('knowledge_facts') else 'No previous context available'}

Create a detailed technical architecture document with technology recommendations, component design, and scalability considerations."""

    def _get_expected_output_format(self) -> str:
        return """A comprehensive technical architecture document including technology stack, component design, scalability strategy, and deployment approach."""

    async def _parse_crew_result(self, result: Any, execution_time_ms: int) -> SolutionArchitectOutput:
        content = str(result)

        # NOTE: Structured parsing not yet implemented - returns basic output with empty structured fields
        return SolutionArchitectOutput(
            content=content,
            confidence_score=0.0,
            validation_result=ValidationResult(passed=False, score=0.0, details={}, missing_sections=[], suggestions=[]),
            metadata={"execution_time_ms": execution_time_ms, "agent_type": "solution_architect"},
            processing_time_ms=execution_time_ms,
            technology_stack=[],  # NOTE: Structured extraction not implemented
            architecture_pattern="",  # NOTE: Pattern extraction not implemented
            component_diagram="",  # NOTE: Diagram extraction not implemented
            data_flow_description="",  # NOTE: Data flow extraction not implemented
            scalability_plan="",  # NOTE: Scalability extraction not implemented
            security_considerations=[],  # NOTE: Security extraction not implemented
            deployment_strategy="",  # NOTE: Deployment extraction not implemented
            technical_risks=[],  # NOTE: Risk extraction not implemented
        )