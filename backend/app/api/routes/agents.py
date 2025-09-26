import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Security, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from app.agents.contracts.base import ProjectContext
from app.agents.orchestration.orchestrator import orchestrator
from app.agents.orchestration.workflow import workflow_engine
from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/agents", tags=["agents"])


# Request/Response Models
class BusinessAnalysisRequest(BaseModel):
    """Request for business analysis step."""

    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")
    user_id: str = Field(..., description="User identifier")
    idea_description: str = Field(
        ..., min_length=10, description="Project idea description"
    )
    language: str = Field(default="en", description="Target language for documents")
    target_audience: str | None = Field(None, description="Known target audience")
    user_clarifications: dict[str, Any] | None = Field(
        None, description="User clarifications"
    )


class ArchitectureDesignRequest(BaseModel):
    """Request for architecture design step."""

    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")
    user_id: str = Field(..., description="User identifier")
    project_description: str = Field(
        ..., min_length=50, description="Project description from business analysis"
    )
    language: str = Field(default="en", description="Target language for documents")
    user_tech_preferences: dict[str, Any] | None = Field(
        None, description="Technology preferences"
    )


class PlanningRequest(BaseModel):
    """Request for implementation planning step."""

    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")
    user_id: str = Field(..., description="User identifier")
    project_description: str = Field(..., description="Project description")
    architecture_overview: str = Field(..., description="Architecture overview")
    language: str = Field(default="en", description="Target language for documents")
    team_size: int | None = Field(None, description="Team size")


class StandardsRequest(BaseModel):
    """Request for engineering standards step."""

    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")
    user_id: str = Field(..., description="User identifier")
    project_description: str = Field(..., description="Project description")
    technology_stack: list[str] = Field(..., description="Technology stack")
    language: str = Field(default="en", description="Target language for documents")
    team_experience_level: str | None = Field(None, description="Team experience level")


class AgentResponse(BaseModel):
    """Standard agent response."""

    status: str = Field(..., description="Execution status")
    content: str | None = Field(None, description="Generated content")
    confidence_score: float = Field(..., description="Agent confidence score")
    validation_result: dict[str, Any] | None = Field(
        None, description="Validation results"
    )
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    error_message: str | None = Field(None, description="Error message if failed")
    correlation_id: str = Field(..., description="Request correlation ID")


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(api_key: str = Security(api_key_header)) -> dict:
    """Simple API key auth; replace with real auth provider."""
    if not api_key:
        logger.warning("Authentication failed: missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    # NOTE: API key validation not implemented - returning 501
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication not implemented",
    )


@router.post("/business-analysis", response_model=AgentResponse)
async def execute_business_analysis(
    request: BusinessAnalysisRequest, current_user: dict | None = None
) -> AgentResponse:
    """Execute business analysis workflow step."""
    if current_user is None:
        current_user = await get_current_user()
    correlation_id = str(uuid.uuid4())

    try:
        # Create project context
        context = ProjectContext(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            current_step=1,
            correlation_id=correlation_id,
            language=request.language,
            user_id=request.user_id,
        )

        logger.info(
            "Starting business analysis execution",
            correlation_id=correlation_id,
            tenant_id=request.tenant_id,
            project_id=request.project_id,
        )

        # Execute workflow step
        result = await workflow_engine.execute_business_analysis(
            context=context,
            idea_description=request.idea_description,
            user_clarifications=request.user_clarifications,
            target_audience=request.target_audience,
        )

        return AgentResponse(correlation_id=correlation_id, **result)

    except Exception as e:
        logger.exception(
            "Business analysis execution failed",
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Business analysis failed",
                "correlation_id": correlation_id,
            },
        ) from e


@router.post("/architecture-design", response_model=AgentResponse)
async def execute_architecture_design(
    request: ArchitectureDesignRequest, current_user: dict | None = None
) -> AgentResponse:
    """Execute architecture design workflow step."""
    if current_user is None:
        current_user = await get_current_user()
    correlation_id = str(uuid.uuid4())

    try:
        context = ProjectContext(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            current_step=3,
            correlation_id=correlation_id,
            language=request.language,
            user_id=request.user_id,
        )

        result = await workflow_engine.execute_architecture_design(
            context=context,
            project_description=request.project_description,
            user_tech_preferences=request.user_tech_preferences,
        )

        return AgentResponse(correlation_id=correlation_id, **result)

    except Exception as e:
        logger.exception(
            "Architecture design execution failed",
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Architecture design failed",
                "correlation_id": correlation_id,
            },
        ) from e


@router.post("/implementation-planning", response_model=AgentResponse)
async def execute_implementation_planning(
    request: PlanningRequest, current_user: dict | None = None
) -> AgentResponse:
    """Execute implementation planning workflow step."""
    if current_user is None:
        current_user = await get_current_user()
    correlation_id = str(uuid.uuid4())

    try:
        context = ProjectContext(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            current_step=4,
            correlation_id=correlation_id,
            language=request.language,
            user_id=request.user_id,
        )

        result = await workflow_engine.execute_implementation_planning(
            context=context,
            project_description=request.project_description,
            architecture_overview=request.architecture_overview,
            team_size=request.team_size,
        )

        return AgentResponse(correlation_id=correlation_id, **result)

    except Exception as e:
        logger.exception(
            "Implementation planning execution failed",
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Implementation planning failed",
                "correlation_id": correlation_id,
            },
        ) from e


@router.post("/engineering-standards", response_model=AgentResponse)
async def execute_engineering_standards(
    request: StandardsRequest, current_user: dict | None = None
) -> AgentResponse:
    """Execute engineering standards workflow step."""
    if current_user is None:
        current_user = await get_current_user()
    correlation_id = str(uuid.uuid4())

    try:
        context = ProjectContext(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            current_step=2,
            correlation_id=correlation_id,
            language=request.language,
            user_id=request.user_id,
        )

        result = await workflow_engine.execute_engineering_standards(
            context=context,
            project_description=request.project_description,
            technology_stack=request.technology_stack,
            team_experience_level=request.team_experience_level,
        )

        return AgentResponse(correlation_id=correlation_id, **result)

    except Exception as e:
        logger.exception(
            "Engineering standards execution failed",
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Engineering standards failed",
                "correlation_id": correlation_id,
            },
        ) from e


@router.get("/health")
async def agent_health_check() -> dict:
    """Health check for agent system."""
    try:
        health = await orchestrator.health_check()
        status_str = health.get("status", "unhealthy")
        code = 200 if status_str == "healthy" else 503
        return JSONResponse(
            content={
                "status": status_str,
                "agent_system": health,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=code,
        )
    except Exception:
        logger.exception("Agent health check failed")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "agent_system": {"status": "unhealthy"},
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=503,
        )


class FullWorkflowRequest(BaseModel):
    """Request for complete workflow execution."""

    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")
    user_id: str = Field(..., description="User identifier")
    idea_description: str = Field(
        ..., min_length=10, description="Project idea description"
    )
    language: str = Field(default="en", description="Target language for documents")
    target_audience: str | None = Field(None, description="Known target audience")
    technology_stack: list[str] | None = Field(
        None, description="Technology stack for engineering standards"
    )
    user_tech_preferences: dict[str, Any] | None = Field(
        None, description="Technology preferences"
    )
    team_size: int | None = Field(None, description="Team size")
    team_experience_level: str | None = Field(None, description="Team experience level")


async def generate_progress_stream(
    workflow_id: str, context: ProjectContext, input_data: dict[str, Any]
) -> AsyncGenerator[str, None]:
    """Generate SSE stream for workflow progress updates."""
    try:
        yield f"data: {json.dumps({'type': 'start', 'workflow_id': workflow_id, 'timestamp': datetime.now(UTC).isoformat()})}\n\n"

        # Step 1: Business Analysis
        yield f"data: {json.dumps({'type': 'step_start', 'step': 1, 'name': 'Business Analysis', 'status': 'running'})}\n\n"
        await asyncio.sleep(0.1)  # Allow client to receive message

        try:
            ba_result = await workflow_engine.execute_business_analysis(
                context=context,
                idea_description=input_data["idea_description"],
                target_audience=input_data.get("target_audience"),
                user_clarifications=input_data.get("user_clarifications"),
            )
            yield f"data: {json.dumps({'type': 'step_complete', 'step': 1, 'status': 'completed', 'confidence': ba_result.get('confidence_score', 0.8)})}\n\n"
        except HTTPException:
            raise
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Business analysis validation error", error=str(e), correlation_id=context.correlation_id)
            yield f"data: {json.dumps({'type': 'step_error', 'step': 1, 'message': f'Business analysis validation failed: {str(e)}', 'correlation_id': context.correlation_id})}\n\n"
            return
        except Exception as e:
            logger.error("Business analysis unexpected error", error=str(e), correlation_id=context.correlation_id, exc_info=True)
            yield f"data: {json.dumps({'type': 'step_error', 'step': 1, 'message': 'Business analysis failed due to system error', 'correlation_id': context.correlation_id})}\n\n"
            return

        # Step 2: Engineering Standards
        context.current_step = 2
        yield f"data: {json.dumps({'type': 'step_start', 'step': 2, 'name': 'Engineering Standards', 'status': 'running'})}\n\n"
        await asyncio.sleep(0.1)

        try:
            # Get default technology stack from configuration
            settings = get_settings()
            tech_stack = (
                input_data.get("technology_stack") or settings.DEFAULT_TECHNOLOGY_STACK
            )

            standards_result = await workflow_engine.execute_engineering_standards(
                context=context,
                project_description=ba_result.get("content", ""),
                technology_stack=tech_stack,
                team_experience_level=input_data.get("team_experience_level"),
            )
            yield f"data: {json.dumps({'type': 'step_complete', 'step': 2, 'status': 'completed', 'confidence': standards_result.get('confidence_score', 0.8)})}\n\n"
        except HTTPException:
            raise
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Engineering standards validation error", error=str(e), correlation_id=context.correlation_id)
            yield f"data: {json.dumps({'type': 'step_error', 'step': 2, 'message': f'Engineering standards validation failed: {str(e)}', 'correlation_id': context.correlation_id})}\n\n"
            return
        except Exception as e:
            logger.error("Engineering standards unexpected error", error=str(e), correlation_id=context.correlation_id, exc_info=True)
            yield f"data: {json.dumps({'type': 'step_error', 'step': 2, 'message': 'Engineering standards failed due to system error', 'correlation_id': context.correlation_id})}\n\n"
            return

        # Step 3: Architecture Design
        context.current_step = 3
        yield f"data: {json.dumps({'type': 'step_start', 'step': 3, 'name': 'Architecture Design', 'status': 'running'})}\n\n"
        await asyncio.sleep(0.1)

        try:
            arch_result = await workflow_engine.execute_architecture_design(
                context=context,
                project_description=ba_result.get("content", ""),
                engineering_standards=standards_result.get("content", ""),
                user_tech_preferences=input_data.get("user_tech_preferences"),
            )
            yield f"data: {json.dumps({'type': 'step_complete', 'step': 3, 'status': 'completed', 'confidence': arch_result.get('confidence_score', 0.8)})}\n\n"
        except HTTPException:
            raise
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Architecture design validation error", error=str(e), correlation_id=context.correlation_id)
            yield f"data: {json.dumps({'type': 'step_error', 'step': 3, 'message': f'Architecture design validation failed: {str(e)}', 'correlation_id': context.correlation_id})}\n\n"
        except Exception as e:
            logger.error("Architecture design unexpected error", error=str(e), correlation_id=context.correlation_id, exc_info=True)
            yield f"data: {json.dumps({'type': 'step_error', 'step': 3, 'message': 'Architecture design failed due to system error', 'correlation_id': context.correlation_id})}\n\n"
            return

        # Step 4: Implementation Planning
        context.current_step = 4
        yield f"data: {json.dumps({'type': 'step_start', 'step': 4, 'name': 'Implementation Planning', 'status': 'running'})}\n\n"
        await asyncio.sleep(0.1)

        try:
            planning_result = await workflow_engine.execute_implementation_planning(
                context=context,
                project_description=ba_result.get("content", ""),
                engineering_standards=standards_result.get("content", ""),
                architecture_overview=arch_result.get("content", ""),
                team_size=input_data.get("team_size"),
            )
            yield f"data: {json.dumps({'type': 'step_complete', 'step': 4, 'status': 'completed', 'confidence': planning_result.get('confidence_score', 0.8)})}\n\n"
        except HTTPException:
            raise
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Implementation planning validation error", error=str(e), correlation_id=context.correlation_id)
            yield f"data: {json.dumps({'type': 'step_error', 'step': 4, 'message': f'Implementation planning validation failed: {str(e)}', 'correlation_id': context.correlation_id})}\n\n"
            return
        except Exception as e:
            logger.error("Implementation planning unexpected error", error=str(e), correlation_id=context.correlation_id, exc_info=True)
            yield f"data: {json.dumps({'type': 'step_error', 'step': 4, 'message': 'Implementation planning failed due to system error', 'correlation_id': context.correlation_id})}\n\n"
            return

        # Workflow complete
        yield f"data: {json.dumps({'type': 'complete', 'workflow_id': workflow_id, 'status': 'completed', 'results': {'business_analysis': ba_result, 'standards': standards_result, 'architecture': arch_result, 'planning': planning_result}})}\n\n"

    except Exception:
        logger.exception("Workflow stream error", workflow_id=workflow_id)
        yield f"data: {json.dumps({'type': 'error', 'workflow_id': workflow_id, 'message': 'Workflow failed'})}\n\n"


@router.post("/workflow/execute-stream")
async def execute_full_workflow_stream(
    request: FullWorkflowRequest, current_user: dict | None = None
) -> StreamingResponse:
    """Execute complete agent workflow with real-time progress updates via SSE."""
    if current_user is None:
        current_user = await get_current_user()
    workflow_id = str(uuid.uuid4())

    context = ProjectContext(
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        current_step=1,
        correlation_id=workflow_id,
        language=request.language,
        user_id=request.user_id,
    )

    input_data = {
        "idea_description": request.idea_description,
        "target_audience": request.target_audience,
        "technology_stack": request.technology_stack,
        "user_tech_preferences": request.user_tech_preferences,
        "team_size": request.team_size,
        "team_experience_level": request.team_experience_level,
    }

    return StreamingResponse(
        generate_progress_stream(workflow_id, context, input_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/workflow/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str, current_user: dict | None = None
) -> dict:
    """Get current workflow execution status."""
    if current_user is None:
        current_user = await get_current_user()
    # NOTE: Workflow status tracking not implemented - returns HTTP 501
    # Should track workflow execution state in Redis or database
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Workflow status tracking not yet implemented",
    )


@router.get("/history/{project_id}")
async def get_agent_execution_history(
    project_id: str, current_user: dict | None = None
) -> dict:
    """Get agent execution history for a project."""
    if current_user is None:
        current_user = await get_current_user()
    # NOTE: Execution history tracking not implemented - returns HTTP 501
    # Should store and retrieve execution history from database
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Agent execution history not yet implemented",
    )
