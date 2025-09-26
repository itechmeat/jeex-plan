"""
Business Analyst Agent implementation.
Specializes in project description, problem analysis, and business requirements.
"""

import json
from typing import Any

from ..base.agent_base import AgentBase
from ..base.quality_control import quality_controller
from ..base.vector_context import vector_context
from ..contracts.base import AgentInput, AgentOutput, ProjectContext, ValidationResult
from ..contracts.business_analyst import BusinessAnalystInput, BusinessAnalystOutput


class BusinessAnalystAgent(AgentBase):
    """Business Analyst specializing in project analysis and requirements gathering."""

    def __init__(self) -> None:
        super().__init__(
            name="Business Analyst",
            role="Senior Business Analyst",
            goal="Transform raw project ideas into comprehensive business requirements with clear problem statements, target audience analysis, and success metrics",
            backstory="""You are an experienced business analyst with 10+ years in product development and startup consulting.
            You excel at asking the right questions to uncover the true business value and user needs behind any project idea.
            Your expertise includes market analysis, user research, business model design, and risk assessment.""",
        )

    def get_input_model(self) -> type[AgentInput]:
        """Return BusinessAnalystInput model."""
        return BusinessAnalystInput

    def get_output_model(self) -> type[AgentOutput]:
        """Return BusinessAnalystOutput model."""
        return BusinessAnalystOutput

    async def validate_input(self, input_data: BusinessAnalystInput) -> None:
        """Validate input data."""
        if (
            not input_data.idea_description
            or len(input_data.idea_description.strip()) < 10
        ):
            raise ValueError("Idea description must be at least 10 characters")

    async def validate_output(
        self, output_data: BusinessAnalystOutput
    ) -> ValidationResult:
        """Validate output using quality controller."""
        correlation_id = output_data.metadata.get("correlation_id", "unknown")
        vr = await quality_controller.validate_agent_output(
            output_data,
            "business_analyst",
            correlation_id,
        )
        # Keep output confidence aligned with QC score
        output_data.confidence_score = vr.score
        return vr

    def get_system_prompt(self, context: ProjectContext) -> str:
        """Generate system prompt for Business Analyst."""
        return f"""You are a Senior Business Analyst specializing in transforming raw ideas into comprehensive business requirements.

**Your Role:**
- Analyze project ideas to identify core business value
- Define clear problem statements and target audiences
- Establish success metrics and business models
- Assess risks and constraints
- Generate clarifying questions for better understanding

**Document Language:** {context.language}

**Key Responsibilities:**
1. **Problem Analysis**: Break down the idea to understand the core problem being solved
2. **Audience Definition**: Identify and analyze target users/customers
3. **Value Proposition**: Articulate the unique value and benefits
4. **Success Metrics**: Define measurable KPIs and goals
5. **Business Model**: Suggest monetization and sustainability approaches
6. **Risk Assessment**: Identify potential risks and mitigation strategies

**Output Requirements:**
- Write in professional business analysis style
- Use clear, structured Markdown with headers
- Include specific, measurable metrics where possible
- Provide actionable insights and recommendations
- Ask intelligent follow-up questions when more clarity is needed

**Document Structure Expected:**
```markdown
# Project Description

## Problem Statement
[Clear definition of the problem being solved]

## Target Audience
[Detailed audience analysis with personas if applicable]

## Value Proposition
[Unique value and competitive advantages]

## Success Metrics & KPIs
[Specific, measurable goals and metrics]

## Business Model Recommendations
[Monetization strategies and revenue models]

## Risk Analysis & Mitigation
[Key risks and proposed mitigation strategies]

## Next Steps & Questions
[Recommended actions and clarifying questions]
```

Focus on depth of analysis rather than breadth. Provide specific, actionable insights."""

    async def get_context_data(self, context: ProjectContext) -> dict[str, Any]:
        """Retrieve relevant context for business analysis."""
        # For step 1, there's usually no prior context
        if context.current_step == 1:
            return {"previous_context": [], "related_projects": []}

        # Get any existing project context
        return await vector_context.get_step_context(context, context.current_step)

    def _build_task_description(
        self, input_data: BusinessAnalystInput, context_data: dict[str, Any]
    ) -> str:
        """Build detailed task description for CrewAI."""
        task_parts = [
            "Analyze the following project idea and create a comprehensive business analysis document:",
            "",
            "**Project Idea:**",
            f"{input_data.idea_description}",
            "",
        ]

        if input_data.target_audience:
            task_parts.extend(
                [
                    "**Known Target Audience:**",
                    f"{input_data.target_audience}",
                    "",
                ]
            )

        if input_data.business_goals:
            task_parts.extend(
                [
                    "**Known Business Goals:**",
                    f"{', '.join(input_data.business_goals)}",
                    "",
                ]
            )

        if input_data.constraints:
            task_parts.extend(
                [
                    "**Known Constraints:**",
                    f"{', '.join(input_data.constraints)}",
                    "",
                ]
            )

        if input_data.user_clarifications:
            task_parts.extend(
                [
                    "**Previous Clarifications:**",
                    f"{json.dumps(input_data.user_clarifications, indent=2)}",
                    "",
                ]
            )

        if context_data.get("documents"):
            task_parts.extend(
                [
                    "**Relevant Context:**",
                    "Consider the following context from previous analysis:",
                ]
            )
            for doc in context_data["documents"][:3]:  # Limit context
                task_parts.append(f"- {doc['content'][:200]}...")
            task_parts.append("")

        task_parts.extend(
            [
                "**Your Task:**",
                "1. Analyze the project idea thoroughly from a business perspective",
                "2. Create a structured business analysis document in Markdown format",
                "3. Focus on problem definition, target audience, value proposition, and business viability",
                "4. Include specific, measurable success metrics and KPIs",
                "5. Assess risks and provide mitigation strategies",
                "6. Generate thoughtful follow-up questions to improve understanding",
                "",
                "**Important:** Extract key facts and insights that should be remembered for future analysis steps.",
            ]
        )

        return "\n".join(task_parts)

    def _get_expected_output_format(self) -> str:
        """Get expected output format for CrewAI."""
        return """A comprehensive business analysis document in Markdown format that includes:

1. **Executive Summary** - Brief overview of the project and its business potential
2. **Problem Statement** - Clear definition of the problem being solved
3. **Target Audience Analysis** - Detailed audience segmentation and personas
4. **Value Proposition** - Unique value and competitive advantages
5. **Success Metrics & KPIs** - Specific, measurable goals and tracking methods
6. **Business Model Recommendations** - Revenue models and monetization strategies
7. **Market Analysis** - Market size, competition, and positioning
8. **Risk Assessment** - Key risks and mitigation strategies
9. **Implementation Recommendations** - Next steps and priority actions
10. **Clarifying Questions** - Strategic questions to improve understanding

The document should be professional, well-structured, and actionable. Include specific examples and recommendations where possible."""

    async def _parse_crew_result(
        self, result: Any, execution_time_ms: int
    ) -> BusinessAnalystOutput:
        """Parse CrewAI result into typed output."""
        content = str(result)

        # Extract key facts for vector storage
        key_facts = self._extract_key_facts(content)

        # Extract structured information
        problem_statement = self._extract_section(
            content, ["Problem Statement", "Problem"]
        )
        target_audience_analysis = self._extract_section(
            content, ["Target Audience", "Audience"]
        )
        success_metrics = self._extract_list_items(
            content, ["Success Metrics", "KPIs", "Metrics"]
        )
        business_model_suggestions = self._extract_list_items(
            content, ["Business Model", "Revenue", "Monetization"]
        )
        risk_analysis = self._extract_list_items(content, ["Risk", "Risks"])
        clarifying_questions = self._extract_list_items(
            content, ["Questions", "Clarifying Questions"]
        )

        return BusinessAnalystOutput(
            content=content,
            confidence_score=0.0,
            validation_result=ValidationResult(
                passed=False, score=0.0, details={}, missing_sections=[], suggestions=[]
            ),
            metadata={
                "execution_time_ms": execution_time_ms,
                "agent_type": "business_analyst",
            },
            processing_time_ms=execution_time_ms,
            key_facts=key_facts,
            problem_statement=problem_statement,
            target_audience_analysis=target_audience_analysis,
            success_metrics=success_metrics,
            business_model_suggestions=business_model_suggestions,
            risk_analysis=risk_analysis,
            clarifying_questions=clarifying_questions,
        )

    def _extract_key_facts(self, content: str) -> list[str]:
        """Extract key facts for vector storage."""
        # Simple extraction based on content analysis
        facts = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if (line.startswith(("- ", "* "))) and len(line) > 20:
                facts.append(line[2:].strip())
            elif line.startswith("**") and line.endswith("**") and len(line) > 10:
                facts.append(line.strip("*").strip())

        return facts[:10]  # Limit to top 10 facts

    def _extract_section(self, content: str, section_names: list[str]) -> str:
        """Extract content from a specific section."""
        for section_name in section_names:
            patterns = [
                f"## {section_name}",
                f"### {section_name}",
                f"**{section_name}**",
            ]
            for pattern in patterns:
                if pattern in content:
                    start_idx = content.find(pattern)
                    if start_idx != -1:
                        start_idx += len(pattern)
                        # Find next section or end
                        next_section = content.find("\n##", start_idx)
                        if next_section == -1:
                            next_section = content.find("\n###", start_idx)
                        if next_section == -1:
                            section_content = content[start_idx:].strip()
                        else:
                            section_content = content[start_idx:next_section].strip()
                        return section_content
        return ""

    def _extract_list_items(self, content: str, section_names: list[str]) -> list[str]:
        """Extract list items from a section."""
        section_content = self._extract_section(content, section_names)
        if not section_content:
            return []

        items = []
        for line in section_content.split("\n"):
            line = line.strip()
            if (line.startswith(("- ", "* "))) and len(line) > 5:
                items.append(line[2:].strip())

        return items
