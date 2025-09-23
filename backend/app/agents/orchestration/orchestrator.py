"""
Agent Orchestrator - manages agent execution and workflow coordination.
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

from ..base.agent_base import AgentBase
from ..base.llm_client import llm_manager
from ..base.vector_context import vector_context
from ..implementations import (
    BusinessAnalystAgent,
    SolutionArchitectAgent,
    ProjectPlannerAgent,
    EngineeringStandardsAgent,
)
from ..contracts.base import (
    ProjectContext,
    AgentExecutionResult,
    ProgressUpdate,
    AgentError,
)
from app.core.logger import get_logger

logger = get_logger()


class WorkflowStep(str, Enum):
    """Workflow step definitions."""
    BUSINESS_ANALYSIS = "business_analysis"
    ARCHITECTURE_DESIGN = "architecture_design"
    IMPLEMENTATION_PLANNING = "implementation_planning"
    ENGINEERING_STANDARDS = "engineering_standards"


class AgentOrchestrator:
    """Main orchestrator for agent workflow execution."""

    def __init__(self):
        self.agents: Dict[WorkflowStep, AgentBase] = {
            WorkflowStep.BUSINESS_ANALYSIS: BusinessAnalystAgent(),
            WorkflowStep.ARCHITECTURE_DESIGN: SolutionArchitectAgent(),
            WorkflowStep.IMPLEMENTATION_PLANNING: ProjectPlannerAgent(),
            WorkflowStep.ENGINEERING_STANDARDS: EngineeringStandardsAgent(),
        }
        self.logger = get_logger("agent_orchestrator")
        self.progress_callbacks: Dict[str, Callable] = {}

    async def initialize(self):
        """Initialize orchestrator and dependencies."""
        try:
            await llm_manager.initialize()
            await vector_context.initialize()
            self.logger.info("Agent orchestrator initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            raise

    def register_progress_callback(self, correlation_id: str, callback: Callable[[ProgressUpdate], None]):
        """Register progress callback for real-time updates."""
        self.progress_callbacks[correlation_id] = callback

    def unregister_progress_callback(self, correlation_id: str):
        """Remove progress callback."""
        self.progress_callbacks.pop(correlation_id, None)

    async def execute_step(
        self,
        step: WorkflowStep,
        context: ProjectContext,
        input_data: Any,
    ) -> AgentExecutionResult:
        """Execute a specific workflow step."""
        start_time = datetime.utcnow()
        correlation_id = context.correlation_id

        try:
            self.logger.info(
                f"Starting workflow step execution",
                step=step.value,
                correlation_id=correlation_id,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
            )

            # Emit progress update
            await self._emit_progress(
                context, f"Starting {step.value}", 0.0, f"Initializing {step.value} agent"
            )

            # Get appropriate agent
            agent = self.agents.get(step)
            if not agent:
                raise AgentError(
                    message=f"No agent found for step {step.value}",
                    agent_type="orchestrator",
                    correlation_id=correlation_id,
                )

            # Validate input data type
            expected_input_type = agent.get_input_model()
            if not isinstance(input_data, expected_input_type):
                raise AgentError(
                    message=f"Invalid input type for {step.value}: expected {expected_input_type.__name__}",
                    agent_type="orchestrator",
                    correlation_id=correlation_id,
                )

            # Execute agent
            await self._emit_progress(
                context, f"Executing {step.value}", 0.2, f"Processing with {agent.name}"
            )

            output_data = await agent.process(input_data)

            # Store result in vector database for future context
            await self._emit_progress(
                context, f"Storing results", 0.8, f"Saving {step.value} output for future context"
            )

            await vector_context.store_agent_output(
                context=context,
                agent_type=step.value,
                content=output_data.content,
                metadata={
                    "confidence_score": output_data.confidence_score,
                    "validation_passed": output_data.validation_result.passed,
                    "step": step.value,
                },
            )

            # Create execution result
            execution_result = AgentExecutionResult(
                agent_type=step.value,
                input_data=input_data,
                output_data=output_data,
                status="completed",
                error_message=None,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            await self._emit_progress(
                context, f"Completed {step.value}", 1.0, f"{agent.name} execution completed successfully"
            )

            self.logger.info(
                f"Workflow step completed successfully",
                step=step.value,
                correlation_id=correlation_id,
                execution_time_ms=execution_result.execution_time_ms,
                confidence_score=output_data.confidence_score,
                validation_passed=output_data.validation_result.passed,
            )

            return execution_result

        except Exception as e:
            execution_result = AgentExecutionResult(
                agent_type=step.value,
                input_data=input_data,
                output_data=None,
                status="failed",
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            await self._emit_progress(
                context, f"Failed {step.value}", 0.0, f"Execution failed: {str(e)}"
            )

            self.logger.error(
                f"Workflow step execution failed",
                step=step.value,
                correlation_id=correlation_id,
                error=str(e),
                execution_time_ms=execution_result.execution_time_ms,
            )

            raise AgentError(
                message=f"Step {step.value} execution failed: {str(e)}",
                agent_type="orchestrator",
                correlation_id=correlation_id,
                details={"step": step.value, "execution_time_ms": execution_result.execution_time_ms},
            )

    async def execute_full_workflow(
        self,
        context: ProjectContext,
        step_inputs: Dict[WorkflowStep, Any],
    ) -> Dict[WorkflowStep, AgentExecutionResult]:
        """Execute complete 4-step workflow."""
        results = {}
        workflow_steps = [
            WorkflowStep.BUSINESS_ANALYSIS,
            WorkflowStep.ARCHITECTURE_DESIGN,
            WorkflowStep.IMPLEMENTATION_PLANNING,
            WorkflowStep.ENGINEERING_STANDARDS,
        ]

        try:
            self.logger.info(
                "Starting full workflow execution",
                correlation_id=context.correlation_id,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                total_steps=len(workflow_steps),
            )

            for i, step in enumerate(workflow_steps, 1):
                # Update context for current step
                current_context = ProjectContext(
                    tenant_id=context.tenant_id,
                    project_id=context.project_id,
                    current_step=i,
                    correlation_id=context.correlation_id,
                    language=context.language,
                    user_id=context.user_id,
                )

                # Get input for this step
                step_input = step_inputs.get(step)
                if step_input is None:
                    # TODO 04: Implement automatic input generation from previous steps
                    raise AgentError(
                        message=f"No input provided for step {step.value}",
                        agent_type="orchestrator",
                        correlation_id=context.correlation_id,
                    )

                # Execute step
                result = await self.execute_step(step, current_context, step_input)
                results[step] = result

                # Brief pause between steps for system stability
                await asyncio.sleep(1)

            self.logger.info(
                "Full workflow execution completed",
                correlation_id=context.correlation_id,
                total_steps=len(workflow_steps),
                successful_steps=len([r for r in results.values() if r.status == "completed"]),
            )

            return results

        except Exception as e:
            self.logger.error(
                "Full workflow execution failed",
                correlation_id=context.correlation_id,
                error=str(e),
                completed_steps=len(results),
            )
            raise

    async def _emit_progress(self, context: ProjectContext, step: str, progress: float, message: str):
        """Emit progress update to registered callbacks."""
        update = ProgressUpdate(
            correlation_id=context.correlation_id,
            step=step,
            progress=progress,
            message=message,
        )

        # Call registered callback if exists
        callback = self.progress_callbacks.get(context.correlation_id)
        if callback:
            try:
                await callback(update)
            except Exception as e:
                self.logger.warning(
                    "Progress callback failed",
                    correlation_id=context.correlation_id,
                    error=str(e),
                )

    async def health_check(self) -> Dict[str, Any]:
        """Health check for orchestrator and dependencies."""
        try:
            # Check LLM manager
            llm_healthy = bool(llm_manager.clients)

            # Check vector context
            vector_health = await vector_context.health_check()

            # Check agents
            agent_count = len(self.agents)

            return {
                "status": "healthy" if llm_healthy and vector_health.get("status") == "healthy" else "degraded",
                "llm_providers": list(llm_manager.clients.keys()) if hasattr(llm_manager, 'clients') else [],
                "vector_database": vector_health,
                "available_agents": agent_count,
                "workflow_steps": [step.value for step in WorkflowStep],
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "available_agents": 0,
                "workflow_steps": [],
            }


# Global orchestrator instance
orchestrator = AgentOrchestrator()