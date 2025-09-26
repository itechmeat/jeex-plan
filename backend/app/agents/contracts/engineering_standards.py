"""
Engineering Standards agent contracts.
Handles code quality standards, review processes, and technical guidelines.
"""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from .base import AgentInput, AgentOutput


class CodeStandard(BaseModel):
    """Code standard definition with rules and examples."""

    category: str = Field(
        ..., description="Standard category (naming, structure, etc.)"
    )
    rules: list[str] = Field(..., description="Specific rules and guidelines")
    examples: dict[str, str] | None = Field(
        None, description="Code examples (good/bad)"
    )
    tools: list[str] = Field(
        default_factory=list, description="Recommended tools for enforcement"
    )


class EngineeringStandardsInput(AgentInput):
    """Input data for Engineering Standards agent."""

    project_description: str = Field(..., description="Complete project description")
    technology_stack: list[str] = Field(..., description="Selected technology stack")
    team_experience_level: str | None = Field(None, description="Team experience level")
    existing_standards: dict[str, Any] | None = Field(
        None, description="Existing team standards"
    )
    compliance_requirements: list[str] | None = Field(
        None, description="Compliance requirements"
    )

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


class EngineeringStandardsOutput(AgentOutput):
    """Output from Engineering Standards agent."""

    coding_standards: list[CodeStandard] = Field(
        ..., description="Code quality standards"
    )
    review_process: str = Field(..., description="Code review process and guidelines")
    definition_of_done: list[str] = Field(
        ..., description="Definition of Done criteria"
    )
    testing_strategy: str = Field(..., description="Testing approach and requirements")
    security_guidelines: list[str] = Field(..., description="Security best practices")
    performance_standards: list[str] = Field(
        ..., description="Performance requirements"
    )
    documentation_requirements: list[str] = Field(
        ..., description="Documentation standards"
    )
    toolchain_recommendations: dict[str, list[str]] = Field(
        default_factory=dict, description="Recommended tools by category"
    )

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
