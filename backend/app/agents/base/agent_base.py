"""
Base agent class with common functionality.
Provides template for all specialized agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import time
import asyncio

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
        agent_verbose = bool(self.llm_config.get("agent_verbose", False))
        agent_memory = bool(self.llm_config.get("agent_memory", False))
        return Agent(
            role=self.role,
            goal=self.goal,
            backstory=self.backstory,
            tools=self.tools,
            verbose=agent_verbose,
            memory=agent_memory,
            system_template=self.get_system_prompt(context),
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
            crew_verbose = bool(self.llm_config.get("crew_verbose", False))
            crew = Crew(agents=[agent], tasks=[task], verbose=crew_verbose)

            # Execute the crew
            import math
            timeout_s = float(self.llm_config.get("timeout_seconds", 120))
            start = time.perf_counter()
            result = await asyncio.wait_for(asyncio.to_thread(crew.kickoff), timeout=timeout_s)
            execution_time_ms = math.floor((time.perf_counter() - start) * 1000)

            # Parse and validate output
            output_data = await self._parse_crew_result(result, execution_time_ms)
            # Ensure correlation_id is set before validation
            output_data.metadata.setdefault("correlation_id", correlation_id)
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

        except AgentError:
            # Already enriched; propagate as-is.
            raise
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.logger.exception(
                "Agent execution failed",
                agent=self.name,
                correlation_id=correlation_id,
                execution_time_ms=execution_time,
            )
            raise AgentError(
                message=f"Agent {self.name} execution failed",
                agent_type=self.name,
                correlation_id=correlation_id,
                details={"execution_time_ms": execution_time, "error": str(e)},
            ) from e

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