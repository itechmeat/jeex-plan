"""
Document generation service.
Orchestrates the four-stage document generation workflow with agent coordination.
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts.base import ProjectContext
from app.agents.orchestration.workflow import workflow_engine
from app.core.logger import get_logger
from app.models.agent_execution import AgentType
from app.models.document_version import DocumentType
from app.models.project import ProjectStatus
from app.repositories.agent_execution import AgentExecutionRepository
from app.repositories.document_version import DocumentVersionRepository
from app.repositories.project import ProjectRepository
from app.services.qdrant import QdrantService

logger = get_logger()


class DocumentGenerationService:
    """Service for managing document generation workflow."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.doc_repo = DocumentVersionRepository(session, tenant_id)
        self.exec_repo = AgentExecutionRepository(session, tenant_id)
        self.project_repo = ProjectRepository(session, tenant_id)
        self.qdrant_service = QdrantService()

    async def execute_business_analysis(
        self,
        project_id: UUID,
        idea_description: str,
        user_id: UUID,
        language: str = "en",
        target_audience: str | None = None,
        user_clarifications: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Step 1: Business Analysis."""
        correlation_id = uuid4()

        # Create project context
        context = ProjectContext(
            tenant_id=str(self.tenant_id),
            project_id=str(project_id),
            current_step=1,
            correlation_id=str(correlation_id),
            language=language,
            user_id=str(user_id),
        )

        # Start execution tracking
        execution = await self.exec_repo.start_execution(
            project_id=project_id,
            agent_type=AgentType.BUSINESS_ANALYST,
            correlation_id=correlation_id,
            input_data={
                "idea_description": idea_description,
                "target_audience": target_audience,
                "user_clarifications": user_clarifications,
            },
            initiated_by=user_id,
        )

        try:
            # Execute business analysis workflow
            result = await workflow_engine.execute_business_analysis(
                context=context,
                idea_description=idea_description,
                user_clarifications=user_clarifications,
                target_audience=target_audience,
            )

            # Short-circuit on failed workflow response
            if result.get("status") not in ("completed", "success"):
                msg = (
                    result.get("error_message")
                    or "Business analysis did not complete successfully"
                )
                await self.exec_repo.fail_execution(execution.id, msg)
                logger.error(
                    "Business analysis returned non-completed status",
                    correlation_id=str(correlation_id),
                    status=result.get("status"),
                    error=msg,
                    project_id=str(project_id),
                    tenant_id=str(self.tenant_id),
                )
                await self.session.commit()
                return {
                    **result,
                    "status": "failed",
                    "error_message": msg,
                    "correlation_id": str(correlation_id),
                }

            # Save document version
            doc_version = await self.doc_repo.create_version(
                project_id=project_id,
                document_type=DocumentType.ABOUT,
                title="Project Description",
                content=result["content"],
                created_by=user_id,
                metadata={
                    "confidence_score": result.get("confidence_score", 0.0),
                    "validation_result": result.get("validation_result", {}),
                    "correlation_id": str(correlation_id),
                },
            )

            # Store key facts in vector database for context
            if "key_facts" in result:
                await self._store_knowledge_vectors(
                    project_id=project_id,
                    document_type=DocumentType.ABOUT.value,
                    content_chunks=result["key_facts"],
                    metadata={
                        "document_id": str(doc_version.id),
                        "version": doc_version.version,
                        "step": 1,
                        "correlation_id": str(correlation_id),
                    },
                )

            # Complete execution
            await self.exec_repo.complete_execution(execution.id, result)

            # Update project status
            await self.project_repo.update(
                project_id, current_step=2, status=ProjectStatus.IN_PROGRESS
            )

            await self.session.commit()

            return {
                "status": "completed",
                "document_id": str(doc_version.id),
                "version": doc_version.version,
                "correlation_id": str(correlation_id),
                **result,
            }

        except Exception as e:
            await self.exec_repo.fail_execution(execution.id, str(e))
            await self.session.rollback()
            logger.exception(
                "Business analysis failed", correlation_id=str(correlation_id)
            )
            raise

    async def execute_engineering_standards(
        self,
        project_id: UUID,
        user_id: UUID,
        technology_stack: list[str],
        language: str = "en",
        team_experience_level: str | None = None,
    ) -> dict[str, Any]:
        """Execute Step 2: Engineering Standards."""
        correlation_id = uuid4()

        # Get project description from previous step
        about_doc = await self.doc_repo.get_latest_version(
            project_id=project_id, document_type=DocumentType.ABOUT
        )

        if not about_doc:
            raise ValueError(
                "Business analysis must be completed before engineering standards"
            )

        # Create project context
        context = ProjectContext(
            tenant_id=str(self.tenant_id),
            project_id=str(project_id),
            current_step=2,
            correlation_id=str(correlation_id),
            language=language,
            user_id=str(user_id),
        )

        # Start execution tracking
        execution = await self.exec_repo.start_execution(
            project_id=project_id,
            agent_type=AgentType.ENGINEERING_STANDARDS,
            correlation_id=correlation_id,
            input_data={
                "project_description": about_doc.content,
                "technology_stack": technology_stack,
                "team_experience_level": team_experience_level,
            },
            initiated_by=user_id,
        )

        try:
            # Execute engineering standards workflow
            result = await workflow_engine.execute_engineering_standards(
                context=context,
                project_description=about_doc.content,
                technology_stack=technology_stack,
                team_experience_level=team_experience_level,
            )

            # Short-circuit on failed workflow response
            if result.get("status") not in ("completed", "success"):
                msg = (
                    result.get("error_message")
                    or "Engineering standards did not complete successfully"
                )
                await self.exec_repo.fail_execution(execution.id, msg)
                logger.error(
                    "Engineering standards returned non-completed status",
                    correlation_id=str(correlation_id),
                    status=result.get("status"),
                    error=msg,
                    project_id=str(project_id),
                    tenant_id=str(self.tenant_id),
                )
                await self.session.commit()
                return {
                    **result,
                    "status": "failed",
                    "error_message": msg,
                    "correlation_id": str(correlation_id),
                }

            # Save document version
            doc_version = await self.doc_repo.create_version(
                project_id=project_id,
                document_type=DocumentType.SPECS,
                title="Engineering Standards",
                content=result["content"],
                created_by=user_id,
                metadata={
                    "confidence_score": result.get("confidence_score", 0.0),
                    "validation_result": result.get("validation_result", {}),
                    "technology_stack": technology_stack,
                    "correlation_id": str(correlation_id),
                },
            )

            # Store standards knowledge in vector database
            if "coding_standards" in result:
                await self._store_knowledge_vectors(
                    project_id=project_id,
                    document_type=DocumentType.SPECS.value,
                    content_chunks=result["coding_standards"],
                    metadata={
                        "document_id": str(doc_version.id),
                        "version": doc_version.version,
                        "step": 2,
                        "correlation_id": str(correlation_id),
                    },
                )

            # Complete execution
            await self.exec_repo.complete_execution(execution.id, result)

            # Update project status
            await self.project_repo.update(project_id, current_step=3)

            await self.session.commit()

            return {
                "status": "completed",
                "document_id": str(doc_version.id),
                "version": doc_version.version,
                "correlation_id": str(correlation_id),
                **result,
            }

        except Exception as e:
            await self.exec_repo.fail_execution(execution.id, str(e))
            await self.session.rollback()
            logger.exception(
                "Engineering standards failed", correlation_id=str(correlation_id)
            )
            raise

    async def execute_architecture_design(
        self,
        project_id: UUID,
        user_id: UUID,
        language: str = "en",
        user_tech_preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Step 3: Architecture Design."""
        correlation_id = uuid4()

        # Get previous documents (about and specs)
        about_doc = await self.doc_repo.get_latest_version(
            project_id=project_id, document_type=DocumentType.ABOUT
        )
        specs_doc = await self.doc_repo.get_latest_version(
            project_id=project_id, document_type=DocumentType.SPECS
        )

        if not about_doc or not specs_doc:
            raise ValueError(
                "Business analysis and engineering standards must be completed before architecture design"
            )

        # Create project context
        context = ProjectContext(
            tenant_id=str(self.tenant_id),
            project_id=str(project_id),
            current_step=3,
            correlation_id=str(correlation_id),
            language=language,
            user_id=str(user_id),
        )

        # Start execution tracking
        execution = await self.exec_repo.start_execution(
            project_id=project_id,
            agent_type=AgentType.SOLUTION_ARCHITECT,
            correlation_id=correlation_id,
            input_data={
                "project_description": about_doc.content,
                "engineering_standards": specs_doc.content,
                "user_tech_preferences": user_tech_preferences,
            },
            initiated_by=user_id,
        )

        try:
            # Execute architecture design workflow with engineering standards context
            result = await workflow_engine.execute_architecture_design(
                context=context,
                project_description=about_doc.content,
                engineering_standards=specs_doc.content,
                user_tech_preferences=user_tech_preferences,
            )

            # Short-circuit on failed workflow response
            if result.get("status") not in ("completed", "success"):
                msg = (
                    result.get("error_message")
                    or "Architecture design did not complete successfully"
                )
                await self.exec_repo.fail_execution(execution.id, msg)
                logger.error(
                    "Architecture design returned non-completed status",
                    correlation_id=str(correlation_id),
                    status=result.get("status"),
                    error=msg,
                    project_id=str(project_id),
                    tenant_id=str(self.tenant_id),
                )
                await self.session.commit()
                return {
                    **result,
                    "status": "failed",
                    "error_message": msg,
                    "correlation_id": str(correlation_id),
                }

            # Save document version
            doc_version = await self.doc_repo.create_version(
                project_id=project_id,
                document_type=DocumentType.ARCHITECTURE,
                title="Technical Architecture",
                content=result["content"],
                created_by=user_id,
                metadata={
                    "confidence_score": result.get("confidence_score", 0.0),
                    "validation_result": result.get("validation_result", {}),
                    "correlation_id": str(correlation_id),
                },
            )

            # Store technical knowledge in vector database
            if "technical_decisions" in result:
                await self._store_knowledge_vectors(
                    project_id=project_id,
                    document_type=DocumentType.ARCHITECTURE.value,
                    content_chunks=result["technical_decisions"],
                    metadata={
                        "document_id": str(doc_version.id),
                        "version": doc_version.version,
                        "step": 3,
                        "correlation_id": str(correlation_id),
                    },
                )

            # Complete execution
            await self.exec_repo.complete_execution(execution.id, result)

            # Update project status
            await self.project_repo.update(project_id, current_step=4)

            await self.session.commit()

            return {
                "status": "completed",
                "document_id": str(doc_version.id),
                "version": doc_version.version,
                "correlation_id": str(correlation_id),
                **result,
            }

        except Exception as e:
            await self.exec_repo.fail_execution(execution.id, str(e))
            await self.session.rollback()
            logger.exception(
                "Architecture design failed", correlation_id=str(correlation_id)
            )
            raise

    async def execute_implementation_planning(
        self,
        project_id: UUID,
        user_id: UUID,
        language: str = "en",
        team_size: int | None = None,
    ) -> dict[str, Any]:
        """Execute Step 4: Implementation Planning."""
        correlation_id = uuid4()

        # Get all previous documents for context
        about_doc = await self.doc_repo.get_latest_version(
            project_id, DocumentType.ABOUT
        )
        specs_doc = await self.doc_repo.get_latest_version(
            project_id, DocumentType.SPECS
        )
        arch_doc = await self.doc_repo.get_latest_version(
            project_id, DocumentType.ARCHITECTURE
        )

        if not about_doc or not specs_doc or not arch_doc:
            raise ValueError(
                "All previous steps (business analysis, engineering standards, architecture) must be completed before implementation planning"
            )

        # Create project context
        context = ProjectContext(
            tenant_id=str(self.tenant_id),
            project_id=str(project_id),
            current_step=4,
            correlation_id=str(correlation_id),
            language=language,
            user_id=str(user_id),
        )

        # Start execution tracking
        execution = await self.exec_repo.start_execution(
            project_id=project_id,
            agent_type=AgentType.PROJECT_PLANNER,
            correlation_id=correlation_id,
            input_data={
                "project_description": about_doc.content,
                "engineering_standards": specs_doc.content,
                "architecture_overview": arch_doc.content,
                "team_size": team_size,
            },
            initiated_by=user_id,
        )

        try:
            # Execute implementation planning workflow with all previous context
            result = await workflow_engine.execute_implementation_planning(
                context=context,
                project_description=about_doc.content,
                engineering_standards=specs_doc.content,
                architecture_overview=arch_doc.content,
                team_size=team_size,
            )

            # Short-circuit on failed workflow response
            if result.get("status") not in ("completed", "success"):
                msg = (
                    result.get("error_message")
                    or "Implementation planning did not complete successfully"
                )
                await self.exec_repo.fail_execution(execution.id, msg)
                logger.error(
                    "Implementation planning returned non-completed status",
                    correlation_id=str(correlation_id),
                    status=result.get("status"),
                    error=msg,
                    project_id=str(project_id),
                    tenant_id=str(self.tenant_id),
                )
                await self.session.commit()
                return {
                    **result,
                    "status": "failed",
                    "error_message": msg,
                    "correlation_id": str(correlation_id),
                }

            # Save overview document
            overview_doc = await self.doc_repo.create_version(
                project_id=project_id,
                document_type=DocumentType.PLAN_OVERVIEW,
                title="Implementation Overview",
                content=result["overview_content"],
                created_by=user_id,
                metadata={
                    "confidence_score": result.get("confidence_score", 0.0),
                    "correlation_id": str(correlation_id),
                },
            )

            # Save individual epic documents
            epic_docs = []
            if "epics" in result:
                for epic in result["epics"]:
                    epic_doc = await self.doc_repo.create_version(
                        project_id=project_id,
                        document_type=DocumentType.PLAN_EPIC,
                        title=epic["title"],
                        content=epic["content"],
                        created_by=user_id,
                        epic_number=epic["number"],
                        epic_name=epic["name"],
                        metadata={
                            "estimated_duration": epic.get("estimated_duration"),
                            "dependencies": epic.get("dependencies", []),
                            "correlation_id": str(correlation_id),
                        },
                    )
                    epic_docs.append(epic_doc)

            # Store planning knowledge in vector database
            # Overview
            await self._store_knowledge_vectors(
                project_id=project_id,
                document_type=DocumentType.PLAN_OVERVIEW.value,
                content_chunks=[result["overview_content"]],
                metadata={
                    "document_id": str(overview_doc.id),
                    "version": overview_doc.version,
                    "step": 4,
                    "correlation_id": str(correlation_id),
                },
            )
            # Epics
            if "epics" in result and epic_docs:
                epic_chunks = []
                epic_metadata = []
                # SECURITY: Use strict=True to detect length mismatches
                for epic, doc in zip(result["epics"], epic_docs, strict=True):
                    epic_chunks.append(epic["content"])
                    epic_metadata.append(
                        {
                            "document_id": str(doc.id),
                            "version": doc.version,
                            "step": 4,
                            "epic_number": doc.epic_number,
                            "epic_name": doc.epic_name,
                            "correlation_id": str(correlation_id),
                        }
                    )
                await self.qdrant_service.upsert_documents(
                    documents=epic_chunks,
                    metadata_list=[
                        {
                            "tenant_id": str(self.tenant_id),
                            "project_id": str(project_id),
                            "document_type": DocumentType.PLAN_EPIC.value,
                            "type": DocumentType.PLAN_EPIC.value,
                            "visibility": "private",
                            **md,
                        }
                        for md in epic_metadata
                    ],
                )

            # Complete execution
            await self.exec_repo.complete_execution(execution.id, result)

            # Update project status to completed
            await self.project_repo.update(project_id, status=ProjectStatus.COMPLETED)

            await self.session.commit()

            return {
                "status": "completed",
                "overview_document_id": str(overview_doc.id),
                "epic_documents": [
                    {
                        "id": str(doc.id),
                        "epic_number": doc.epic_number,
                        "title": doc.title,
                    }
                    for doc in epic_docs
                ],
                "correlation_id": str(correlation_id),
                **result,
            }

        except Exception as e:
            await self.exec_repo.fail_execution(execution.id, str(e))
            await self.session.rollback()
            logger.exception(
                "Implementation planning failed", correlation_id=str(correlation_id)
            )
            raise

    async def get_project_progress(self, project_id: UUID) -> dict[str, Any]:
        """Get current project progress and status."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        # Get document versions
        documents = await self.doc_repo.get_project_documents(project_id)
        # Normalize keys and preserve multiple epics
        doc_by_type: dict[str, Any] = {}
        for doc in documents:
            key = (
                doc.document_type.value
                if hasattr(doc.document_type, "value")
                else str(doc.document_type)
            )
            if key == DocumentType.PLAN_EPIC.value:
                doc_by_type.setdefault(key, []).append(doc)
            else:
                doc_by_type[key] = doc

        # Get execution stats
        exec_stats = await self.exec_repo.get_execution_stats(project_id)

        # Calculate progress based on new workflow order
        steps_completed = 0
        if DocumentType.ABOUT.value in doc_by_type:
            steps_completed = 1
        if DocumentType.SPECS.value in doc_by_type:
            steps_completed = 2
        if DocumentType.ARCHITECTURE.value in doc_by_type:
            steps_completed = 3
        if DocumentType.PLAN_OVERVIEW.value in doc_by_type:
            steps_completed = 4

        progress_percentage = (steps_completed / 4) * 100

        return {
            "project_id": str(project_id),
            "status": project.status.value,
            "current_step": project.current_step,
            "progress_percentage": progress_percentage,
            "steps_completed": steps_completed,
            "documents": {
                doc_type: (
                    [
                        {
                            "id": str(d.id),
                            "version": d.version,
                            "title": d.title,
                            "epic_number": d.epic_number,
                            "epic_name": d.epic_name,
                            "created_at": d.created_at.isoformat(),
                        }
                        for d in docs
                    ]
                    if isinstance(docs, list)
                    else {
                        "id": str(docs.id),
                        "version": docs.version,
                        "title": docs.title,
                        "created_at": docs.created_at.isoformat(),
                    }
                )
                for doc_type, docs in doc_by_type.items()
            },
            "execution_stats": exec_stats,
            "updated_at": project.updated_at.isoformat(),
        }

    async def _store_knowledge_vectors(
        self,
        project_id: UUID,
        document_type: str,
        content_chunks: list[str],
        metadata: dict[str, Any],
    ) -> None:
        """Store content chunks in vector database for context retrieval."""
        try:
            base_metadata = {
                "tenant_id": str(self.tenant_id),
                "project_id": str(project_id),
                "document_type": document_type,
                "type": document_type,
                "category": "knowledge",
                "visibility": "private",
                **metadata,
            }

            await self.qdrant_service.upsert_documents(
                documents=content_chunks,
                metadata_list=[base_metadata.copy() for _ in content_chunks],
            )

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "Vector database connection failed",
                error=str(e),
                correlation_id=metadata.get("correlation_id"),
                project_id=str(project_id),
                tenant_id=str(self.tenant_id),
                document_type=document_type,
            )
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(
                "Invalid data for vector storage",
                error=str(e),
                correlation_id=metadata.get("correlation_id"),
                project_id=str(project_id),
                tenant_id=str(self.tenant_id),
                document_type=document_type,
            )
        except Exception as e:
            logger.warning(
                "Failed to store knowledge vectors",
                error=str(e),
                correlation_id=metadata.get("correlation_id"),
                project_id=str(project_id),
                tenant_id=str(self.tenant_id),
                document_type=document_type,
                exc_info=True,
            )
            # Don't fail the main operation if vector storage fails
