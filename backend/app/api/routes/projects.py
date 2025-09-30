"""Project management endpoints with multi-tenancy support."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.project import (
    DocumentInfo,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.core.auth import get_current_active_user_dependency
from app.core.database import get_db
from app.core.logger import get_logger
from app.middleware.tenant import get_current_tenant_id
from app.models.rbac import Permission
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.services.rbac import RBACService

router = APIRouter()
logger = get_logger(__name__)


def _status_value(status: object) -> str:
    """Return string representation for enum or plain status."""
    return status.value if hasattr(status, "value") else str(status)


def _project_current_step(project: object) -> int:
    """Safely extract current step with default."""
    current_step = getattr(project, "current_step", None)
    try:
        return int(current_step) if current_step is not None else 1
    except (TypeError, ValueError):
        return 1


def _project_language(project: object, fallback: str = "en") -> str:
    """Safely extract language value."""
    language = getattr(project, "language", None)
    return language or fallback


def _project_steps_completed(project: object) -> list[int]:
    """Return completed steps if available."""
    steps = getattr(project, "steps_completed", None)
    if steps is None:
        return []
    if isinstance(steps, list):
        return steps
    try:
        return list(steps)
    except TypeError:
        return []


def _handle_integrity_error(
    ie: IntegrityError,
    name_field: str | None = None,
    operation: str = "operation",
) -> HTTPException:
    """Convert IntegrityError to appropriate HTTPException with sanitized messages.

    Args:
        ie: The IntegrityError caught from database operation
        name_field: The project name that was attempted (for 409 responses)
        operation: Description of the operation for logging (e.g., "create", "update")

    Returns:
        HTTPException with appropriate status code and sanitized message

    Note:
        Full error details are logged server-side for diagnostics,
        but clients receive sanitized messages to avoid leaking DB internals.
    """
    # Log full error details server-side for diagnostics
    logger.warning(
        "IntegrityError during project %s",
        operation,
        error_type=type(ie).__name__,
        error_message=str(ie),
        original_error=str(ie.orig) if hasattr(ie, "orig") else None,
        attempted_name=name_field,
    )

    # Check if this is specifically a name uniqueness violation
    if "uq_project_tenant_name" in str(ie.orig):
        attempted_name = name_field or "unknown"
        return HTTPException(
            status_code=409,
            detail=f"Project name '{attempted_name}' already exists in this tenant",
        )

    # Other integrity errors (foreign key violations, etc.)
    # Return sanitized message without exposing DB internals
    return HTTPException(
        status_code=400,
        detail="Database constraint violation. Please check your input.",
    )


def _document_versions_loaded(project: object) -> list:
    """Return preloaded document_versions without triggering lazy load."""
    return project.__dict__.get("document_versions", []) or []  # type: ignore[attr-defined]


def _documents_loaded(project: object) -> list:
    """Return preloaded documents without triggering lazy load."""
    return project.__dict__.get("documents", []) or []  # type: ignore[attr-defined]


def _map_document_version(version_obj: object) -> DocumentInfo:
    """Convert DocumentVersion ORM object to API schema."""
    doc_type = getattr(version_obj, "document_type", "")
    if hasattr(doc_type, "value"):
        doc_type = doc_type.value
    return DocumentInfo(
        id=str(version_obj.id),
        type=str(doc_type),
        version=int(getattr(version_obj, "version", 1) or 1),
        title=getattr(version_obj, "title", ""),
        created_at=version_obj.created_at,
        updated_at=version_obj.updated_at,
    )


def _map_document(document_obj: object) -> DocumentInfo:
    """Convert Document ORM object to API schema."""
    doc_type = getattr(document_obj, "document_type", "")
    if hasattr(doc_type, "value"):
        doc_type = doc_type.value
    return DocumentInfo(
        id=str(document_obj.id),
        type=str(doc_type),
        version=int(getattr(document_obj, "version", 1) or 1),
        title=getattr(document_obj, "title", ""),
        created_at=document_obj.created_at,
        updated_at=document_obj.updated_at,
    )


def _project_documents(project: object) -> list[DocumentInfo]:
    """Collect document metadata if already loaded."""
    documents: list[DocumentInfo] = []

    for version in _document_versions_loaded(project):
        documents.append(_map_document_version(version))

    if not documents:
        for document in _documents_loaded(project):
            documents.append(_map_document(document))

    return documents


def _to_project_response(
    project: object, *, language_fallback: str = "en"
) -> ProjectResponse:
    """Map ORM project instance to ProjectResponse schema."""
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        status=_status_value(project.status),
        current_step=_project_current_step(project),
        language=_project_language(project, language_fallback),
        created_at=project.created_at,
        updated_at=project.updated_at,
        documents=_project_documents(project),
        steps_completed=_project_steps_completed(project),
    )


def _to_project_list_response(
    project: object, *, language_fallback: str = "en"
) -> ProjectListResponse:
    """Map ORM project instance to ProjectListResponse schema."""
    return ProjectListResponse(
        id=str(project.id),
        name=project.name,
        status=_status_value(project.status),
        current_step=_project_current_step(project),
        language=_project_language(project, language_fallback),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/projects", response_model=list[ProjectListResponse])
async def list_projects(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> list[ProjectListResponse]:
    """
    List projects for the current tenant with proper authentication and authorization.

    Returns paginated list of projects with optional filtering and tenant isolation.
    """
    logger.info(
        "Listing projects",
        skip=skip,
        limit=limit,
        status=status,
        tenant_id=str(tenant_id),
        user_id=str(current_user.id),
    )

    # Create repository with tenant isolation
    project_repo = ProjectRepository(db, tenant_id)
    rbac_service = RBACService(db, tenant_id)

    # Check user permissions
    can_list_projects = await rbac_service.check_permission(
        current_user.id,
        None,
        Permission.PROJECT_READ,
    )
    if not can_list_projects:
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to list projects"
        )

    try:
        # Get projects with optional status filtering
        filters = {}
        if status:
            from app.models.project import ProjectStatus

            try:
                status_enum = ProjectStatus(status.upper())
                filters["status"] = status_enum
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: {[s.value for s in ProjectStatus]}",
                )

        projects = await project_repo.get_all(skip=skip, limit=limit, filters=filters)

        # Convert to response format using persisted attributes
        project_responses = [_to_project_list_response(project) for project in projects]

        logger.info(
            "Projects listed successfully",
            count=len(project_responses),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )

        return project_responses

    except (ConnectionError, TimeoutError) as e:
        logger.error(
            "Database connection failed while listing projects",
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=500, detail="Failed to list projects")
    except (ValueError, KeyError, TypeError) as e:
        logger.error(
            "Validation error while listing projects",
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=400, detail="Invalid request parameters")
    except Exception as e:
        logger.error(
            "Failed to list projects",
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to list projects")


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: Request,
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> ProjectResponse:
    """
    Create a new project with proper authentication, authorization and tenant isolation.

    Creates a project with multi-tenancy isolation and initial setup.
    """
    logger.info(
        "Creating project",
        name=project_data.name,
        tenant_id=str(tenant_id),
        user_id=str(current_user.id),
    )

    project_repo = ProjectRepository(db, tenant_id)
    rbac_service = RBACService(db, tenant_id)

    # SECURITY: Require write permission to create projects in this tenant
    can_create = await rbac_service.check_permission(
        current_user.id, None, Permission.PROJECT_WRITE
    )
    if not can_create:
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to create projects"
        )

    try:
        # Remove TOCTOU race condition - rely on database unique constraint
        # instead of checking name availability beforehand
        try:
            project = await project_repo.create(
                name=project_data.name,
                description=getattr(project_data, "description", ""),
                language=getattr(project_data, "language", "en"),
                owner_id=current_user.id,
            )
        except IntegrityError as ie:
            await db.rollback()
            raise _handle_integrity_error(
                ie, name_field=project_data.name, operation="create"
            )

        # Initialize project permissions for the owner
        await rbac_service.add_project_member(
            project_id=project.id,
            user_id=current_user.id,
            role_name="OWNER",
            invited_by_id=current_user.id,
        )

        await db.commit()
        await db.refresh(project)

        logger.info(
            "Project created successfully",
            project_id=str(project.id),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )

        return _to_project_response(project)

    except HTTPException:
        await db.rollback()
        raise
    except (ConnectionError, TimeoutError) as e:
        await db.rollback()
        logger.error(
            "Database connection failed while creating project",
            name=project_data.name,
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=500, detail=f"Database connection error: {e!s}")
    except (ValueError, KeyError, TypeError) as e:
        await db.rollback()
        logger.error(
            "Validation error while creating project",
            name=project_data.name,
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=400, detail=f"Invalid project data: {e!s}")
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error while creating project",
            name=project_data.name,
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e!s}")


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> ProjectResponse:
    """
    Get detailed project information with proper authentication and tenant isolation.

    Returns project details including current step, documents, and progress.
    """
    logger.info(
        "Getting project",
        project_id=str(project_id),
        tenant_id=str(tenant_id),
        user_id=str(current_user.id),
    )

    # Create repository with tenant isolation
    project_repo = ProjectRepository(db, tenant_id)
    rbac_service = RBACService(db, tenant_id)

    # Check user permissions
    can_read_projects = await rbac_service.check_permission(
        current_user.id,
        project_id,
        Permission.PROJECT_READ,
    )
    if not can_read_projects:
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to access projects"
        )

    try:
        # Get project with tenant isolation
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Convert to response format using persisted attributes
        response = _to_project_response(project)

        logger.info(
            "Project retrieved successfully",
            project_id=str(project_id),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )

        return response

    except HTTPException:
        raise
    except (ConnectionError, TimeoutError) as e:
        logger.error(
            "Database connection failed while getting project",
            project_id=str(project_id),
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve project")
    except (ValueError, KeyError, TypeError) as e:
        logger.error(
            "Validation error while getting project",
            project_id=str(project_id),
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=400, detail="Invalid project ID")
    except Exception as e:
        logger.error(
            "Failed to get project",
            project_id=str(project_id),
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve project")


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> ProjectResponse:
    """Update project metadata within tenant boundaries."""
    logger.info(
        "Updating project",
        project_id=str(project_id),
        tenant_id=str(tenant_id),
        user_id=str(current_user.id),
    )

    project_repo = ProjectRepository(db, tenant_id)
    rbac_service = RBACService(db, tenant_id)

    can_update_projects = await rbac_service.check_permission(
        current_user.id,
        project_id,
        Permission.PROJECT_WRITE,
    )
    if not can_update_projects:
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to update projects"
        )

    try:
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        update_fields: dict[str, Any] = {}

        if project_update.name is not None:
            is_available = await project_repo.check_name_availability(
                project_update.name, exclude_project_id=project_id
            )
            if not is_available:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Project name '{project_update.name}' is already taken within tenant"
                    ),
                )
            update_fields["name"] = project_update.name

        if project_update.language is not None:
            logger.warning(
                "Project language updates are not yet persisted",
                project_id=str(project_id),
                tenant_id=str(tenant_id),
                user_id=str(current_user.id),
                requested_language=project_update.language,
            )

        if not update_fields:
            logger.info(
                "No mutable fields supplied for project update",
                project_id=str(project_id),
                tenant_id=str(tenant_id),
                user_id=str(current_user.id),
            )
            return _to_project_response(
                project,
                language_fallback=project_update.language or _project_language(project),
            )

        try:
            updated_project = await project_repo.update(project_id, **update_fields)
            await db.commit()
        except IntegrityError as ie:
            await db.rollback()
            attempted_name = update_fields.get("name")
            raise _handle_integrity_error(
                ie, name_field=attempted_name, operation="update"
            )

        target_project = updated_project or project

        logger.info(
            "Project updated successfully",
            project_id=str(project_id),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )

        return _to_project_response(
            target_project,
            language_fallback=project_update.language
            or _project_language(target_project),
        )

    except HTTPException:
        await db.rollback()
        raise
    except (ConnectionError, TimeoutError) as e:
        await db.rollback()
        logger.error(
            "Database connection failed while updating project",
            project_id=str(project_id),
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=500, detail=f"Database connection error: {e!s}")
    except (ValueError, KeyError, TypeError) as e:
        await db.rollback()
        logger.error(
            "Validation error while updating project",
            project_id=str(project_id),
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=400, detail=f"Invalid project data: {e!s}")
    except Exception as e:
        await db.rollback()
        logger.error(
            "Unexpected error while updating project",
            project_id=str(project_id),
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e!s}")


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> dict[str, str]:
    """Soft delete a project while preserving tenant isolation."""
    logger.info(
        "Deleting project",
        project_id=str(project_id),
        tenant_id=str(tenant_id),
        user_id=str(current_user.id),
    )

    project_repo = ProjectRepository(db, tenant_id)
    rbac_service = RBACService(db, tenant_id)

    can_delete_projects = await rbac_service.check_permission(
        current_user.id,
        project_id,
        Permission.PROJECT_DELETE,
    )
    if not can_delete_projects:
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to delete projects"
        )

    try:
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        deleted = await project_repo.delete(project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")

        await db.commit()

        logger.info(
            "Project deleted successfully",
            project_id=str(project_id),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )

        return {"message": "Project deleted successfully"}

    except HTTPException:
        await db.rollback()
        raise
    except (ConnectionError, TimeoutError) as e:
        await db.rollback()
        logger.error(
            "Database connection failed while deleting project",
            project_id=str(project_id),
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(status_code=500, detail="Failed to delete project")
    except Exception as e:
        await db.rollback()
        logger.error(
            "Failed to delete project",
            project_id=str(project_id),
            error=str(e),
            tenant_id=str(tenant_id),
            user_id=str(current_user.id),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.post("/projects/{project_id}/step1")
async def generate_description_document(
    project_id: str, input_data: dict, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Step 1: Generate Project Description document.

    Business Analyst agent processes the idea and creates initial description.
    """
    logger.info("Generating description document", project_id=project_id)

    # NOTE: actual agent orchestration
    # 1. Validate project exists and user has access
    # 2. Invoke Business Analyst agent
    # 3. Stream progress updates via SSE
    # 4. Save generated document

    # Mock response for MVP
    return {
        "message": "Project description generation started",
        "project_id": project_id,
        "step": 1,
        "status": "processing",
        "estimated_duration": 30,  # seconds
    }


@router.post("/projects/{project_id}/step2")
async def generate_standards_document(
    project_id: str, input_data: dict, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Step 2: Generate Engineering Standards document.

    Engineering Standards agent creates development guidelines and specifications.
    """
    logger.info("Generating engineering standards document", project_id=project_id)

    # NOTE: actual agent orchestration
    # 1. Validate project exists and has completed step 1
    # 2. Invoke Engineering Standards agent
    # 3. Stream progress updates via SSE
    # 4. Save generated document

    # Mock response for MVP
    return {
        "message": "Engineering standards generation started",
        "project_id": project_id,
        "step": 2,
        "status": "processing",
        "estimated_duration": 40,  # seconds
    }


@router.post("/projects/{project_id}/step3")
async def generate_architecture_document(
    project_id: str, input_data: dict, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Step 3: Generate Architecture document.

    Solution Architect agent creates technical architecture document.
    """
    logger.info("Generating architecture document", project_id=project_id)

    # NOTE: actual agent orchestration
    # 1. Validate project exists and has completed steps 1-2
    # 2. Invoke Solution Architect agent
    # 3. Stream progress updates via SSE
    # 4. Save generated document

    # Mock response for MVP
    return {
        "message": "Architecture generation started",
        "project_id": project_id,
        "step": 3,
        "status": "processing",
        "estimated_duration": 45,  # seconds
    }


@router.post("/projects/{project_id}/step4")
async def generate_implementation_plan(
    project_id: str, input_data: dict, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Step 4: Generate Implementation Plan.

    Project Planner agent creates implementation roadmap and epics.
    """
    logger.info("Generating implementation plan", project_id=project_id)

    # NOTE: actual agent orchestration
    # 1. Validate project exists and has completed steps 1-3
    # 2. Invoke Project Planner agent
    # 3. Stream progress updates via SSE
    # 4. Save generated document

    # Mock response for MVP
    return {
        "message": "Implementation plan generation started",
        "project_id": project_id,
        "step": 4,
        "status": "processing",
        "estimated_duration": 60,  # seconds
    }


@router.post("/projects/{project_id}/export")
async def export_project_documents(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Export all project documents as a ZIP archive.

    Creates a downloadable package with all project documentation.
    """
    logger.info("Exporting project documents", project_id=project_id)

    # NOTE: actual export functionality
    # 1. Validate project exists and has required documents
    # 2. Gather active document versions
    # 3. Generate manifest and structure
    # 4. Create ZIP archive
    # 5. Return download URL

    # Mock response for MVP
    return {
        "message": "Export started",
        "project_id": project_id,
        "export_id": "export_123",
        "status": "processing",
        "estimated_duration": 10,  # seconds
    }


@router.get("/projects/{project_id}/progress")
async def get_project_progress(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get current progress of all project generation steps.
    """
    logger.info("Getting project progress", project_id=project_id)

    # NOTE: actual progress tracking
    # 1. Validate project exists and user has access
    # 2. Get current step status
    # 3. Get document generation progress
    # 4. Return comprehensive progress information

    # Mock response for MVP
    return {
        "project_id": project_id,
        "current_step": 1,
        "steps": {
            "step1": {"status": "completed", "progress": 100, "document_id": "doc_123"},
            "step2": {"status": "pending", "progress": 0},
            "step3": {"status": "pending", "progress": 0},
            "step4": {"status": "pending", "progress": 0},
        },
        "overall_progress": 25,
    }
