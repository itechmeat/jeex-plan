"""
Engineering Standards agent contracts.
Handles code quality standards, review processes, and technical guidelines.
"""

from typing import Dict, List, Optional, Any, ClassVar
from pydantic import BaseModel, Field, ConfigDict
from .base import AgentInput, AgentOutput


class CodeStandard(BaseModel):
    """Code standard definition with rules and examples."""

    category: str = Field(
        ..., description="Standard category (naming, structure, etc.)"
    )
    rules: List[str] = Field(..., description="Specific rules and guidelines")
    examples: Optional[Dict[str, str]] = Field(
        None, description="Code examples (good/bad)"
    )
    tools: List[str] = Field(
        default_factory=list, description="Recommended tools for enforcement"
    )


class EngineeringStandardsInput(AgentInput):
    """Input data for Engineering Standards agent."""

    project_description: str = Field(..., description="Complete project description")
    technology_stack: List[str] = Field(..., description="Selected technology stack")
    team_experience_level: Optional[str] = Field(
        None, description="Team experience level"
    )
    existing_standards: Optional[Dict[str, Any]] = Field(
        None, description="Existing team standards"
    )
    compliance_requirements: Optional[List[str]] = Field(
        None, description="Compliance requirements"
    )

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


class EngineeringStandardsOutput(AgentOutput):
    """Output from Engineering Standards agent."""

    coding_standards: List[CodeStandard] = Field(
        ..., description="Code quality standards"
    )
    review_process: str = Field(..., description="Code review process and guidelines")
    definition_of_done: List[str] = Field(
        ..., description="Definition of Done criteria"
    )
    testing_strategy: str = Field(..., description="Testing approach and requirements")
    security_guidelines: List[str] = Field(..., description="Security best practices")
    performance_standards: List[str] = Field(
        ..., description="Performance requirements"
    )
    documentation_requirements: List[str] = Field(
        ..., description="Documentation standards"
    )
    toolchain_recommendations: Dict[str, List[str]] = Field(
        default_factory=dict, description="Recommended tools by category"
    )

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
