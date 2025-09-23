"""
Quality control and validation for agent outputs.
Ensures content quality and completeness.
"""

import re
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

import textstat
import markdown

from app.core.logger import get_logger
from ..contracts.base import ValidationResult, AgentOutput

logger = get_logger()


class ContentValidator(ABC):
    """Abstract base class for content validators."""

    @abstractmethod
    async def validate(self, content: str, _metadata: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate content and return results."""
        pass


class MarkdownValidator(ContentValidator):
    """Validates Markdown content structure and quality."""

    def __init__(self):
        self.required_sections = [
            "# ",  # At least one H1 header
        ]
        self.preferred_sections = [
            "## ",  # H2 headers for structure
            "### ",  # H3 headers for subsections
        ]

    async def validate(self, content: str, _metadata: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate Markdown content."""
        checks = []
        missing_sections = []
        suggestions = []

        # Check for required sections
        for section in self.required_sections:
            if section in content:
                checks.append(True)
            else:
                checks.append(False)
                missing_sections.append(f"Missing: {section.strip()}")

        # Check for preferred structure
        has_h2 = "## " in content
        has_h3 = "### " in content

        if not has_h2:
            suggestions.append("Consider adding H2 headers (##) for better structure")
        if not has_h3:
            suggestions.append("Consider adding H3 headers (###) for detailed structure")

        # Check for lists and formatting
        has_lists = bool(re.search(r'^\s*[-*+]\s', content, re.MULTILINE))
        has_numbered_lists = bool(re.search(r'^\s*\d+\.\s', content, re.MULTILINE))

        if not (has_lists or has_numbered_lists):
            suggestions.append("Consider adding lists for better readability")

        # Check for code blocks or examples
        has_code_blocks = "```" in content
        has_inline_code = "`" in content and not has_code_blocks

        if not (has_code_blocks or has_inline_code):
            suggestions.append("Consider adding code examples or technical references")

        # Try to parse as Markdown
        try:
            html = markdown.markdown(content)
            html_length = len(html)
            markdown_quality = min(1.0, html_length / 1000)  # Normalize by expected length
        except Exception:
            suggestions.append("Markdown syntax may have issues")
            markdown_quality = 0.5

        # Calculate overall score
        structure_score = sum(checks) / len(checks) if checks else 0.0
        content_score = len(content) / 2000  # Normalize by expected length
        quality_score = markdown_quality

        # Bonus points for good structure and formatting
        formatting_bonus = 0.0
        if has_h2 and has_h3:
            formatting_bonus += 0.1  # Good heading structure
        if has_lists or has_numbered_lists:
            formatting_bonus += 0.05  # Good list usage
        if has_code_blocks or has_inline_code:
            formatting_bonus += 0.05  # Good code examples

        overall_score = min(1.0, (structure_score + min(1.0, content_score) + quality_score) / 3 + formatting_bonus)

        return ValidationResult(
            passed=overall_score >= 0.7,
            score=overall_score,
            details={
                "structure_score": structure_score,
                "content_length": len(content),
                "has_headers": has_h2 or has_h3,
                "has_lists": has_lists or has_numbered_lists,
                "has_code": has_code_blocks or has_inline_code,
                "markdown_quality": markdown_quality,
            },
            missing_sections=missing_sections,
            suggestions=suggestions,
        )


class ReadabilityValidator(ContentValidator):
    """Validates content readability using textstat."""

    def __init__(self):
        self.target_grade_level = 12  # College level
        self.min_reading_ease = 30  # Somewhat difficult

    async def validate(self, content: str, _metadata: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate content readability."""
        suggestions = []

        try:
            # Calculate readability metrics
            flesch_ease = textstat.flesch_reading_ease(content)
            flesch_grade = textstat.flesch_kincaid_grade(content)
            automated_readability = textstat.automated_readability_index(content)

            # Analyze sentence and word complexity
            avg_sentence_length = textstat.avg_sentence_length(content)
            syllable_count = textstat.syllable_count(content)
            word_count = textstat.lexicon_count(content)

            # Generate suggestions based on metrics
            if flesch_ease < self.min_reading_ease:
                suggestions.append("Content may be too complex - consider shorter sentences")

            if flesch_grade > self.target_grade_level + 2:
                suggestions.append("Grade level is high - consider simpler vocabulary")

            if avg_sentence_length > 25:
                suggestions.append("Average sentence length is high - break up long sentences")

            # Calculate score based on multiple factors
            ease_score = min(1.0, flesch_ease / 60)  # Normalize to 0-1
            grade_score = max(0.0, 1.0 - (flesch_grade - self.target_grade_level) / 10)
            length_score = min(1.0, word_count / 1000)  # Normalize by expected word count

            # Calculate syllable complexity (lower is better for readability)
            avg_syllables_per_word = syllable_count / word_count if word_count > 0 else 0
            syllable_score = max(0.0, 1.0 - (avg_syllables_per_word - 1.5) / 2)  # Optimal around 1.5 syllables per word

            overall_score = (ease_score + grade_score + length_score + syllable_score) / 4

            return ValidationResult(
                passed=overall_score >= 0.6,
                score=overall_score,
                details={
                    "flesch_reading_ease": flesch_ease,
                    "flesch_kincaid_grade": flesch_grade,
                    "automated_readability_index": automated_readability,
                    "avg_sentence_length": avg_sentence_length,
                    "word_count": word_count,
                    "syllable_count": syllable_count,
                },
                missing_sections=[],
                suggestions=suggestions,
            )

        except Exception as e:
            logger.warning(f"Readability validation failed: {e}")
            return ValidationResult(
                passed=True,  # Don't fail if readability check fails
                score=0.7,  # Neutral score
                details={"error": str(e)},
                missing_sections=[],
                suggestions=["Readability analysis unavailable"],
            )


class BusinessAnalystValidator(ContentValidator):
    """Specialized validator for Business Analyst outputs."""

    def __init__(self):
        self.required_sections = [
            "problem",
            "target audience",
            "success metrics",
            "business model",
            "risk",
        ]

    async def validate(self, content: str, _metadata: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate Business Analyst document."""
        content_lower = content.lower()
        checks = []
        missing_sections = []

        for section in self.required_sections:
            if section in content_lower:
                checks.append(True)
            else:
                checks.append(False)
                missing_sections.append(f"Missing section: {section}")

        # Check for specific business analysis elements
        has_metrics = any(keyword in content_lower for keyword in ["kpi", "metric", "measure", "target"])
        has_audience = any(keyword in content_lower for keyword in ["user", "customer", "audience", "stakeholder"])
        has_value_prop = any(keyword in content_lower for keyword in ["value", "benefit", "advantage", "solution"])

        business_elements = [has_metrics, has_audience, has_value_prop]
        business_score = sum(business_elements) / len(business_elements)

        structure_score = sum(checks) / len(checks)
        overall_score = (structure_score + business_score) / 2

        suggestions = []
        if not has_metrics:
            suggestions.append("Add specific success metrics and KPIs")
        if not has_audience:
            suggestions.append("Provide more detail about target audience")
        if not has_value_prop:
            suggestions.append("Clarify the value proposition")

        return ValidationResult(
            passed=overall_score >= 0.7,
            score=overall_score,
            details={
                "structure_score": structure_score,
                "business_score": business_score,
                "has_metrics": has_metrics,
                "has_audience": has_audience,
                "has_value_proposition": has_value_prop,
            },
            missing_sections=missing_sections,
            suggestions=suggestions,
        )


class SolutionArchitectValidator(ContentValidator):
    """Specialized validator for Solution Architect outputs."""

    def __init__(self):
        self.required_sections = [
            "technology stack",
            "architecture",
            "component",
            "scalability",
            "security",
        ]

    async def validate(self, content: str, _metadata: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate Solution Architect document."""
        content_lower = content.lower()
        checks = []
        missing_sections = []

        for section in self.required_sections:
            if section in content_lower:
                checks.append(True)
            else:
                checks.append(False)
                missing_sections.append(f"Missing section: {section}")

        # Check for technical elements
        has_diagram = "```mermaid" in content or "diagram" in content_lower
        has_technologies = any(tech in content_lower for tech in [
            "database", "frontend", "backend", "api", "server", "client"
        ])
        has_patterns = any(pattern in content_lower for pattern in [
            "pattern", "microservice", "monolith", "mvc", "rest", "graphql"
        ])

        technical_elements = [has_diagram, has_technologies, has_patterns]
        technical_score = sum(technical_elements) / len(technical_elements)

        structure_score = sum(checks) / len(checks)
        overall_score = (structure_score + technical_score) / 2

        suggestions = []
        if not has_diagram:
            suggestions.append("Consider adding architecture diagrams")
        if not has_technologies:
            suggestions.append("Specify more technology choices")
        if not has_patterns:
            suggestions.append("Explain architectural patterns used")

        return ValidationResult(
            passed=overall_score >= 0.7,
            score=overall_score,
            details={
                "structure_score": structure_score,
                "technical_score": technical_score,
                "has_diagram": has_diagram,
                "has_technologies": has_technologies,
                "has_patterns": has_patterns,
            },
            missing_sections=missing_sections,
            suggestions=suggestions,
        )


class QualityController:
    """Main quality control system for agent outputs."""

    def __init__(self):
        self.validators = {
            "markdown": MarkdownValidator(),
            "readability": ReadabilityValidator(),
            "business_analyst": BusinessAnalystValidator(),
            "solution_architect": SolutionArchitectValidator(),
        }
        self.logger = get_logger("quality_controller")

    async def validate_agent_output(
        self,
        output: AgentOutput,
        agent_type: str,
        correlation_id: str,
    ) -> ValidationResult:
        """Validate agent output with appropriate validators."""
        try:
            # Always run basic validators
            validators_to_run = ["markdown", "readability"]

            # Add specialized validator based on agent type
            if agent_type.lower().replace("_", "").replace("-", "") in self.validators:
                validators_to_run.append(agent_type.lower().replace("_", "").replace("-", ""))

            results = []
            all_suggestions = []
            all_missing_sections = []
            details = {}

            for validator_name in validators_to_run:
                if validator_name in self.validators:
                    result = await self.validators[validator_name].validate(output.content)
                    results.append(result)
                    all_suggestions.extend(result.suggestions)
                    all_missing_sections.extend(result.missing_sections)
                    details[f"{validator_name}_validation"] = result.details

            # Calculate combined score
            if results:
                combined_score = sum(r.score for r in results) / len(results)
                all_passed = all(r.passed for r in results)
            else:
                combined_score = 0.5
                all_passed = False

            self.logger.info(
                "Agent output validation completed",
                agent_type=agent_type,
                correlation_id=correlation_id,
                validators_used=validators_to_run,
                combined_score=combined_score,
                passed=all_passed,
            )

            return ValidationResult(
                passed=all_passed,
                score=combined_score,
                details=details,
                missing_sections=list(set(all_missing_sections)),  # Remove duplicates
                suggestions=list(set(all_suggestions)),  # Remove duplicates
            )

        except Exception as e:
            self.logger.error(
                "Quality control validation failed",
                agent_type=agent_type,
                correlation_id=correlation_id,
                error=str(e),
            )
            return ValidationResult(
                passed=False,
                score=0.0,
                details={"error": str(e)},
                missing_sections=["Validation failed"],
                suggestions=["Manual review required due to validation error"],
            )


# Global quality controller instance
quality_controller = QualityController()