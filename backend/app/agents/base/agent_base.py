"""
Base agent class with common functionality.
Provides template for all specialized agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import time

from crewai import Agent, Task, Crew

from ..contracts.base import (
    ProjectContext,
    AgentInput,
    AgentOutput,
    ValidationResult,
    ProgressUpdate,
    AgentError,
)
from app.core.logger import get_logger

logger = get_logger()


class AgentBase(ABC):
    """Base class for all JEEX Plan agents."""

    def __init__(
        self,
        name: str,
        role: str,
        goal: str,
        backstory: str,
        tools: Optional[List[Any]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize base agent."""
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []
        self.llm_config = llm_config or {}
        self.logger = get_logger(f"agent.{name.lower().replace(' ', '_')}")

    @abstractmethod
    def get_input_model(self) -> Type[AgentInput]:
        """Return the Pydantic model for agent input."""
        pass

    @abstractmethod
    def get_output_model(self) -> Type[AgentOutput]:
        """Return the Pydantic model for agent output."""
        pass

    @abstractmethod
    async def validate_input(self, input_data: AgentInput) -> None:
        """Validate input data before processing."""
        pass

    @abstractmethod
    async def validate_output(self, output_data: AgentOutput) -> ValidationResult:
        """Validate output data after processing."""
        pass

    @abstractmethod
    def get_system_prompt(self, context: ProjectContext) -> str:
        """Generate system prompt based on context."""
        pass

    @abstractmethod
    async def get_context_data(self, context: ProjectContext) -> Dict[str, Any]:
        """Retrieve relevant context from vector store."""
        pass

    def create_crew_agent(self, context: ProjectContext) -> Agent:
        """Create CrewAI agent instance."""
        return Agent(
            role=self.role,
            goal=self.goal,
            backstory=self.backstory,
            tools=self.tools,
            verbose=True,
            memory=True,
            system_message=self.get_system_prompt(context),
        )

    def create_crew_task(self, agent: Agent, input_data: AgentInput, context_data: Dict[str, Any]) -> Task:
        """Create CrewAI task for agent execution."""
        task_description = self._build_task_description(input_data, context_data)

        return Task(
            description=task_description,
            agent=agent,
            expected_output=self._get_expected_output_format(),
        )

    @abstractmethod
    def _build_task_description(self, input_data: AgentInput, context_data: Dict[str, Any]) -> str:
        """Build task description for CrewAI."""
        pass

    @abstractmethod
    def _get_expected_output_format(self) -> str:
        """Get expected output format for CrewAI task."""
        pass

    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Main processing method - executes the agent."""
        start_time = datetime.utcnow()
        correlation_id = input_data.context.correlation_id

        try:
            self.logger.info(
                f"Starting agent execution",
                agent=self.name,
                correlation_id=correlation_id,
                tenant_id=input_data.context.tenant_id,
                project_id=input_data.context.project_id,
            )

            # Validate input
            await self.validate_input(input_data)

            # Get relevant context
            context_data = await self.get_context_data(input_data.context)

            # Create CrewAI components
            agent = self.create_crew_agent(input_data.context)
            task = self.create_crew_task(agent, input_data, context_data)
            crew = Crew(agents=[agent], tasks=[task], verbose=True)

            # Execute the crew
            execution_start = time.time()
            result = crew.kickoff()
            execution_time_ms = int((time.time() - execution_start) * 1000)

            # Parse and validate output
            output_data = await self._parse_crew_result(result, execution_time_ms)
            validation_result = await self.validate_output(output_data)
            output_data.validation_result = validation_result

            # Log success
            self.logger.info(
                f"Agent execution completed successfully",
                agent=self.name,
                correlation_id=correlation_id,
                execution_time_ms=execution_time_ms,
                confidence_score=output_data.confidence_score,
            )

            return output_data

        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.logger.error(
                f"Agent execution failed",
                agent=self.name,
                correlation_id=correlation_id,
                error=str(e),
                execution_time_ms=execution_time,
            )
            raise AgentError(
                message=f"Agent {self.name} execution failed: {str(e)}",
                agent_type=self.name,
                correlation_id=correlation_id,
                details={"execution_time_ms": execution_time},
            )

    @abstractmethod
    async def _parse_crew_result(self, result: Any, execution_time_ms: int) -> AgentOutput:
        """Parse CrewAI execution result into typed output."""
        pass

    def emit_progress(self, context: ProjectContext, step: str, progress: float, message: str) -> ProgressUpdate:
        """Emit progress update for streaming."""
        return ProgressUpdate(
            correlation_id=context.correlation_id,
            step=step,
            progress=progress,
            message=message,
        )