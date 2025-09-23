"""
Base contracts and data models for agent system.
Defines core types and validation for agent communication.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid


class ProjectContext(BaseModel):
    """Execution context shared across all agents."""

    tenant_id: str = Field(..., description="Tenant identifier for isolation")
    project_id: str = Field(..., description="Project identifier")
    current_step: int = Field(..., ge=1, le=4, description="Current workflow step (1-4)")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request correlation ID")
    language: str = Field(default="en", description="Target language for generated documents")
    user_id: str = Field(..., description="User identifier for audit trail")

    model_config = {"extra": "forbid"}


class AgentInput(BaseModel, ABC):
    """Base class for all agent inputs."""

    context: ProjectContext = Field(..., description="Execution context")

    model_config = {"extra": "forbid"}


class ValidationResult(BaseModel):
    """Result of content validation."""

    passed: bool = Field(..., description="Whether validation passed")
    score: float = Field(..., ge=0.0, le=1.0, description="Quality score (0-1)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Validation details")
    missing_sections: List[str] = Field(default_factory=list, description="Missing required sections")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class AgentOutput(BaseModel, ABC):
    """Base class for all agent outputs."""

    content: str = Field(..., description="Generated document content")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Agent confidence in output quality")
    validation_result: ValidationResult = Field(..., description="Content validation results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    model_config = {"extra": "forbid"}


class AgentExecutionResult(BaseModel):
    """Complete agent execution result with audit trail."""

    agent_type: str = Field(..., description="Type of agent that executed")
    input_data: AgentInput = Field(..., description="Original input data")
    output_data: AgentOutput = Field(..., description="Generated output")
    status: str = Field(..., description="Execution status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: datetime = Field(..., description="Execution completion time")

    @property
    def execution_time_ms(self) -> int:
        """Calculate execution time in milliseconds."""
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return 0


class ProgressUpdate(BaseModel):
    """Progress update for streaming to clients."""

    correlation_id: str = Field(..., description="Request correlation ID")
    step: str = Field(..., description="Current processing step")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage")
    message: str = Field(..., description="Human-readable progress message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional progress details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")


class AgentError(Exception):
    """Base exception for agent-related errors."""

    def __init__(self, message: str, agent_type: str, correlation_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.agent_type = agent_type
        self.correlation_id = correlation_id
        self.details = details or {}


class ValidationError(AgentError):
    """Exception for validation failures."""
    pass


class LLMError(AgentError):
    """Exception for LLM API failures."""
    pass


class ContextRetrievalError(AgentError):
    """Exception for vector context retrieval failures."""
    pass