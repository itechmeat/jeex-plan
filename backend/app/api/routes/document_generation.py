"""
Document generation API routes.
Handles the four-stage document generation workflow with SSE streaming.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_dependency
from app.core.database import get_db
from app.core.logger import get_logger
from app.middleware.tenant import get_current_tenant_id
from app.models.user import User
from app.services.document_generation import DocumentGenerationService
from app.services.export import ExportService
from app.services.streaming import StreamingService

logger = get_logger()
router = APIRouter(prefix="/projects", tags=["Document Generation"])


# Request Models
class BusinessAnalysisRequest(BaseModel):
    """Request for business analysis step."""

    idea_description: str = Field(
        ..., min_length=10, max_length=10000, description="Project idea description"
    )
    language: str = Field(default="en", description="Target language for documents")
    target_audience: str | None = Field(
        None, max_length=1000, description="Known target audience"
    )
    user_clarifications: dict[str, Any] | None = Field(
        None, description="User clarifications"
    )


class ArchitectureDesignRequest(BaseModel):
    """Request for architecture design step."""

    language: str = Field(default="en", description="Target language for documents")
    user_tech_preferences: dict[str, Any] | None = Field(
        None, description="Technology preferences"
    )


class ImplementationPlanningRequest(BaseModel):
    """Request for implementation planning step."""

    language: str = Field(default="en", description="Target language for documents")
    team_size: int | None = Field(None, ge=1, le=100, description="Team size")


class EngineeringStandardsRequest(BaseModel):
    """Request for engineering standards step."""

    technology_stack: Annotated[
        list[str], Field(min_items=1, description="Technology stack")
    ]
    language: str = Field(default="en", description="Target language for documents")
    team_experience_level: str | None = Field(None, description="Team experience level")


class ExportRequest(BaseModel):
    """Request for project export."""

    format: str = Field(default="zip", description="Export format")
    expires_in_hours: int = Field(
        default=24, ge=1, le=168, description="Export expiration in hours"
    )


# Response Models
class DocumentGenerationResponse(BaseModel):
    """Response for document generation steps."""

    status: str
    document_id: str | None = None
    version: int | None = None
    correlation_id: str
    confidence_score: float | None = None
    execution_time_ms: int | None = None
    validation_result: dict[str, Any] | None = None


class ProgressResponse(BaseModel):
    """Response for project progress."""

    project_id: str
    status: str
    current_step: int
    progress_percentage: float
    steps_completed: int
    documents: dict[str, Any]
    execution_stats: dict[str, Any]
    updated_at: str


class ExportResponse(BaseModel):
    """Response for export creation."""

    export_id: str
    status: str
    expires_at: str
    manifest: dict[str, Any]


# Dependencies
def get_document_generation_service(
    db: AsyncSession = Depends(get_db), tenant_id: UUID = Depends(get_current_tenant_id)
) -> DocumentGenerationService:
    """Get document generation service."""
    return DocumentGenerationService(db, tenant_id)


def get_streaming_service() -> StreamingService:
    """Get streaming service."""
    return StreamingService()


def get_export_service(
    db: AsyncSession = Depends(get_db), tenant_id: UUID = Depends(get_current_tenant_id)
) -> ExportService:
    """Get export service."""
    return ExportService(db, tenant_id)


# Routes
@router.post("/{project_id}/step1", response_model=DocumentGenerationResponse)
async def execute_business_analysis(
    project_id: UUID,
    request: BusinessAnalysisRequest,
    service: DocumentGenerationService = Depends(get_document_generation_service),
    streaming: StreamingService = Depends(get_streaming_service),
    user: User = Depends(get_current_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> DocumentGenerationResponse:
    """Execute Step 1: Business Analysis - About Document."""
    try:
        # Publish step start event
        await streaming.publish_step_start(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=1,
            step_name="Business Analysis",
        )

        # Execute business analysis
        result = await service.execute_business_analysis(
            project_id=project_id,
            idea_description=request.idea_description,
            user_id=user.id,
            language=request.language,
            target_audience=request.target_audience,
            user_clarifications=request.user_clarifications,
        )

        # Publish completion event
        await streaming.publish_step_complete(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=1,
            step_name="Business Analysis",
            document_id=result["document_id"],
            confidence_score=result.get("confidence_score", 0.0),
            correlation_id=result["correlation_id"],
        )

        return DocumentGenerationResponse(**result)

    except ValueError as e:
        await streaming.publish_step_error(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=1,
            step_name="Business Analysis",
            error_message="Invalid request",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request parameters"
        ) from e
    except Exception as e:
        await streaming.publish_step_error(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=1,
            step_name="Business Analysis",
            error_message="Internal server error",
        )
        logger.exception("Business analysis failed for project %s", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Business analysis failed",
        ) from e


@router.post("/{project_id}/step2", response_model=DocumentGenerationResponse)
async def execute_engineering_standards(
    project_id: UUID,
    request: EngineeringStandardsRequest,
    service: DocumentGenerationService = Depends(get_document_generation_service),
    streaming: StreamingService = Depends(get_streaming_service),
    user: User = Depends(get_current_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> DocumentGenerationResponse:
    """Execute Step 2: Engineering Standards - Specs Document."""
    try:
        await streaming.publish_step_start(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=2,
            step_name="Engineering Standards",
        )

        result = await service.execute_engineering_standards(
            project_id=project_id,
            user_id=user.id,
            technology_stack=request.technology_stack,
            language=request.language,
            team_experience_level=request.team_experience_level,
        )

        await streaming.publish_step_complete(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=2,
            step_name="Engineering Standards",
            document_id=result["document_id"],
            confidence_score=result.get("confidence_score", 0.0),
            correlation_id=result["correlation_id"],
        )

        return DocumentGenerationResponse(**result)

    except ValueError as e:
        await streaming.publish_step_error(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=2,
            step_name="Engineering Standards",
            error_message="Invalid request",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Precondition failed"
        ) from e
    except Exception as e:
        await streaming.publish_step_error(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=2,
            step_name="Engineering Standards",
            error_message="Internal server error",
        )
        logger.exception("Engineering standards failed for project %s", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Engineering standards failed",
        ) from e


@router.post("/{project_id}/step3", response_model=DocumentGenerationResponse)
async def execute_architecture_design(
    project_id: UUID,
    request: ArchitectureDesignRequest,
    service: DocumentGenerationService = Depends(get_document_generation_service),
    streaming: StreamingService = Depends(get_streaming_service),
    user: User = Depends(get_current_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> DocumentGenerationResponse:
    """Execute Step 3: Architecture Design - Architecture Document."""
    try:
        await streaming.publish_step_start(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=3,
            step_name="Architecture Design",
        )

        result = await service.execute_architecture_design(
            project_id=project_id,
            user_id=user.id,
            language=request.language,
            user_tech_preferences=request.user_tech_preferences,
        )

        await streaming.publish_step_complete(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=3,
            step_name="Architecture Design",
            document_id=result["document_id"],
            confidence_score=result.get("confidence_score", 0.0),
            correlation_id=result["correlation_id"],
        )

        return DocumentGenerationResponse(**result)

    except ValueError as e:
        await streaming.publish_step_error(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=3,
            step_name="Architecture Design",
            error_message="Invalid request",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Precondition failed"
        ) from e
    except Exception as e:
        await streaming.publish_step_error(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=3,
            step_name="Architecture Design",
            error_message="Internal server error",
        )
        logger.exception("Architecture design failed for project %s", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Architecture design failed",
        ) from e


@router.post("/{project_id}/step4", response_model=DocumentGenerationResponse)
async def execute_implementation_planning(
    project_id: UUID,
    request: ImplementationPlanningRequest,
    service: DocumentGenerationService = Depends(get_document_generation_service),
    streaming: StreamingService = Depends(get_streaming_service),
    user: User = Depends(get_current_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> DocumentGenerationResponse:
    """Execute Step 4: Implementation Planning - Plans Documents."""
    try:
        await streaming.publish_step_start(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=4,
            step_name="Implementation Planning",
        )

        result = await service.execute_implementation_planning(
            project_id=project_id,
            user_id=user.id,
            language=request.language,
            team_size=request.team_size,
        )

        await streaming.publish_step_complete(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=4,
            step_name="Implementation Planning",
            document_id=result["overview_document_id"],
            confidence_score=result.get("confidence_score", 0.0),
            correlation_id=result["correlation_id"],
        )

        # Publish workflow completion
        await streaming.publish_workflow_complete(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            correlation_id=result["correlation_id"],
        )

        return DocumentGenerationResponse(**result)

    except ValueError as e:
        await streaming.publish_step_error(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=4,
            step_name="Implementation Planning",
            error_message="Invalid request",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Precondition failed"
        ) from e
    except Exception as e:
        await streaming.publish_step_error(
            tenant_id=str(tenant_id),
            project_id=str(project_id),
            step=4,
            step_name="Implementation Planning",
            error_message="Internal server error",
        )
        logger.exception("Implementation planning failed for project %s", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Implementation planning failed",
        ) from e


@router.get("/{project_id}/progress", response_model=ProgressResponse)
async def get_project_progress(
    project_id: UUID,
    service: DocumentGenerationService = Depends(get_document_generation_service),
) -> ProgressResponse:
    """Get current project progress and status."""
    try:
        progress = await service.get_project_progress(project_id)
        return ProgressResponse(**progress)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from e
    except Exception as e:
        logger.exception("Failed to get project %s progress", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get progress",
        ) from e


@router.get("/{project_id}/events")
async def stream_project_events(
    project_id: UUID,
    streaming: StreamingService = Depends(get_streaming_service),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> StreamingResponse:
    """Stream real-time project events via SSE."""
    return StreamingResponse(
        streaming.stream_project_events(
            tenant_id=str(tenant_id), project_id=str(project_id)
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@router.get("/{project_id}/progress/stream")
async def stream_progress_updates(
    project_id: UUID,
    streaming: StreamingService = Depends(get_streaming_service),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> StreamingResponse:
    """Stream real-time progress updates via SSE."""
    return StreamingResponse(
        streaming.stream_progress_updates(
            tenant_id=str(tenant_id), project_id=str(project_id)
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@router.post("/{project_id}/export", response_model=ExportResponse)
async def create_project_export(
    project_id: UUID,
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    export_service: ExportService = Depends(get_export_service),
    user: User = Depends(get_current_user_dependency),
) -> ExportResponse:
    """Create ZIP export of project documents."""
    try:
        # Create export record
        export = await export_service.create_export(
            project_id=project_id,
            user_id=user.id,
            export_format=request.format,
            expires_in_hours=request.expires_in_hours,
        )

        # Generate export in background
        background_tasks.add_task(
            _generate_export_background, export_service, export.id
        )

        return ExportResponse(
            export_id=str(export.id),
            status=export.status.value,
            expires_at=export.expires_at.isoformat(),
            manifest=export.manifest,
        )

    except ValueError as e:
        logger.exception("Invalid export request for project %s", project_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid export parameters"
        ) from e
    except Exception as e:
        logger.exception("Failed to create export for project %s", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from e


@router.get("/exports/{export_id}")
async def download_export(
    export_id: UUID, export_service: ExportService = Depends(get_export_service)
) -> FileResponse:
    """Download project export ZIP file."""
    try:
        file_path = await export_service.get_export_file_path(export_id)

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export not found or expired",
            )

        # Return file for download
        return FileResponse(
            path=file_path,
            media_type="application/zip",
            filename=f"project-export-{export_id}.zip",
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.exception("Invalid export ID %s", export_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        ) from e
    except Exception as e:
        logger.exception("Failed to download export %s", export_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download export",
        ) from e


async def _generate_export_background(
    export_service: ExportService, export_id: UUID
) -> None:
    """Background task to generate export file."""
    try:
        await export_service.generate_export(export_id)
        logger.info("Export %s generated successfully", export_id)

    except (ConnectionError, TimeoutError) as exc:
        logger.error(
            "Connection failed during export generation for export %s: %s",
            export_id,
            exc,
        )
    except (ValueError, KeyError, TypeError) as exc:
        logger.error(
            "Validation error during export generation for export %s: %s",
            export_id,
            exc,
        )
    except Exception as exc:
        logger.error(
            "Failed to generate export %s: %s",
            export_id,
            exc,
            exc_info=True,
        )


@router.get("/{project_id}/documents")
async def get_project_documents(
    project_id: UUID,
    service: DocumentGenerationService = Depends(get_document_generation_service),
) -> dict[str, Any]:
    """Get all document versions for a project."""
    try:
        documents = await service.doc_repo.get_project_documents(project_id)

        return {
            "project_id": str(project_id),
            "documents": [
                {
                    "id": str(doc.id),
                    "document_type": doc.document_type,
                    "version": doc.version,
                    "title": doc.title,
                    "epic_number": doc.epic_number,
                    "epic_name": doc.epic_name,
                    "created_at": doc.created_at.isoformat(),
                    "created_by": str(doc.created_by),
                    "metadata": doc.document_metadata,
                }
                for doc in documents
            ],
        }

    except ValueError as e:
        logger.exception("Invalid project ID %s", project_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from e
    except Exception as e:
        logger.exception("Failed to get project %s documents", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get documents",
        ) from e


@router.get("/{project_id}/documents/{document_id}/content")
async def get_document_content(
    project_id: UUID,
    document_id: UUID,
    service: DocumentGenerationService = Depends(get_document_generation_service),
) -> dict[str, Any]:
    """Get content of a specific document version."""
    try:
        document = await service.doc_repo.get_by_id(document_id)

        if not document or document.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        return {
            "id": str(document.id),
            "document_type": document.document_type,
            "version": document.version,
            "title": document.title,
            "content": document.content,
            "epic_number": document.epic_number,
            "epic_name": document.epic_name,
            "created_at": document.created_at.isoformat(),
            "metadata": document.document_metadata,
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.exception("Invalid document ID %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        ) from e
    except Exception as e:
        logger.exception("Failed to get document content for %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document",
        ) from e
