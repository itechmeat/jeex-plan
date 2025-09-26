"""
Vector context retrieval for agents.
Integrates with Qdrant for project-specific knowledge retrieval.
"""

from datetime import UTC, datetime
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

# Lazy import of EmbeddingService to avoid initialization issues
from app.adapters.qdrant import QdrantAdapter
from app.core.config import settings
from app.core.logger import get_logger

from ..contracts.base import ContextRetrievalError, ProjectContext

logger = get_logger()


class VectorContextRetriever:
    """Retrieves relevant context from vector database."""

    def __init__(self) -> None:
        self.client: AsyncQdrantClient | None = None
        self.collection_name = settings.QDRANT_COLLECTION
        self.logger = get_logger("vector_context")
        self._embedding_service = None
        self._qdrant_adapter: QdrantAdapter | None = None

    async def initialize(self) -> None:
        """Initialize Qdrant client."""
        try:
            self.client = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
            self.logger.info("Vector context retriever initialized")
        except (ConnectionError, TimeoutError) as exc:
            self.logger.error(
                "Failed to connect to Qdrant", error=str(exc)
            )
            raise
        except (ValueError, TypeError) as exc:
            self.logger.error(
                "Invalid Qdrant configuration", error=str(exc)
            )
            raise
        except Exception as exc:
            self.logger.exception(
                "Unexpected error initializing Qdrant client", error=str(exc)
            )
            raise

    async def get_project_context(
        self,
        context: ProjectContext,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Retrieve relevant context for a project."""
        if not self.client:
            await self.initialize()

        try:
            # Create filter for tenant and project isolation
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="tenant_id", match=MatchValue(value=context.tenant_id)
                    ),
                    FieldCondition(
                        key="project_id", match=MatchValue(value=context.project_id)
                    ),
                ]
            )

            # Perform text-based query search
            search_results = await self.client.query(
                collection_name=self.collection_name,
                query_text=query,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
            )

            # Extract and organize results
            context_data = {
                "query": query,
                "total_results": len(search_results),
                "documents": [],
                "knowledge_facts": [],
                "memories": [],
            }

            for result in search_results:
                payload = result.get("payload", {}) if isinstance(result, dict) else {}
                document_data = {
                    "content": payload.get("text", ""),
                    "type": payload.get("type", "unknown"),
                    "version": payload.get("version", "1"),
                    "score": (
                        result.get("score", 0.0) if isinstance(result, dict) else 0.0
                    ),
                    "metadata": {
                        k: v
                        for k, v in payload.items()
                        if k
                        not in ["text", "type", "version", "tenant_id", "project_id"]
                    },
                }

                context_data["documents"].append(document_data)

                # Categorize by type
                if payload.get("type") == "knowledge":
                    context_data["knowledge_facts"].append(document_data)
                elif payload.get("type") == "memory":
                    context_data["memories"].append(document_data)

            self.logger.info(
                "Retrieved project context",
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                query_length=len(query),
                results_count=len(search_results),
            )

            return context_data

        except (ConnectionError, TimeoutError) as e:
            self.logger.error(
                "Connection error retrieving project context",
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            raise ContextRetrievalError(
                message=f"Vector database connection failed: {e!s}",
                agent_type="vector_context",
                correlation_id=context.correlation_id,
                details={"query": query, "error": str(e)},
            )
        except (ValueError, KeyError, TypeError) as e:
            self.logger.error(
                "Data validation error retrieving project context",
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            raise ContextRetrievalError(
                message=f"Vector context data validation failed: {e!s}",
                agent_type="vector_context",
                correlation_id=context.correlation_id,
                details={"query": query, "error": str(e)},
            )
        except Exception as e:
            self.logger.exception(
                "Unexpected error retrieving project context",
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            raise ContextRetrievalError(
                message=f"Vector context retrieval failed: {e!s}",
                agent_type="vector_context",
                correlation_id=context.correlation_id,
                details={"query": query, "error": str(e)},
            )

    async def get_step_context(
        self,
        context: ProjectContext,
        step: int,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Get context specific to a workflow step."""
        step_queries = {
            1: "project description business requirements target audience problem statement",
            2: "technical architecture technology stack system design components",
            3: "implementation plan project timeline tasks epics milestones",
            4: "engineering standards code quality testing documentation guidelines",
        }

        query = step_queries.get(step, "project context")
        return await self.get_project_context(context, query, limit)

    async def get_previous_steps_context(
        self,
        context: ProjectContext,
        current_step: int,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get context from all previous workflow steps."""
        if current_step <= 1:
            return {"documents": [], "knowledge_facts": [], "memories": []}

        # Build query based on previous steps
        queries = []
        if current_step > 1:
            queries.append("project description business analysis")
        if current_step > 2:
            queries.append("technical architecture system design")
        if current_step > 3:
            queries.append("implementation plan project timeline")

        combined_query = " ".join(queries)
        return await self.get_project_context(context, combined_query, limit)

    async def store_agent_output(
        self,
        context: ProjectContext,
        agent_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store agent output in vector database for future context."""
        try:
            # Generate embeddings for the content
            embedding_metadata = {
                "tenant_id": context.tenant_id,
                "project_id": context.project_id,
                "correlation_id": context.correlation_id,
                **(metadata or {}),
            }

            # Initialize embedding service lazily
            if self._embedding_service is None:
                from app.services.embedding import EmbeddingService

                self._embedding_service = EmbeddingService()

            embedding_result = await self._embedding_service.process_document(
                text=content, doc_type="memory", metadata=embedding_metadata
            )

            # Prepare payloads for each chunk
            payloads = []
            vectors = []

            for chunk, embedding in zip(
                embedding_result.chunks, embedding_result.embeddings, strict=False
            ):
                chunk_payload = {
                    "text": chunk.text,
                    "agent_type": agent_type,
                    "step": context.current_step,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "created_at": datetime.now(UTC).isoformat(),
                    **(metadata or {}),
                }
                payloads.append(chunk_payload)
                vectors.append(embedding)

            # Initialize Qdrant adapter lazily
            if self._qdrant_adapter is None:
                self._qdrant_adapter = QdrantAdapter()

            result = await self._qdrant_adapter.upsert_points(
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                vectors=vectors,
                payloads=payloads,
                doc_type="memory",
                visibility="private",
                version="1",
                lang=context.language,
            )

            self.logger.info(
                "Stored agent output in vector database",
                agent_type=agent_type,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                content_length=len(content),
                chunks_count=len(embedding_result.chunks),
                points_stored=result.get("points_count", 0),
            )

        except (ConnectionError, TimeoutError) as e:
            self.logger.error(
                "Connection error storing agent output",
                agent_type=agent_type,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            # Don't raise exception for storage failures - it's not critical for agent execution
        except (ValueError, KeyError, TypeError) as e:
            self.logger.error(
                "Data validation error storing agent output",
                agent_type=agent_type,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            # Don't raise exception for storage failures - it's not critical for agent execution
        except (ImportError, ModuleNotFoundError) as e:
            self.logger.error(
                "Module import error storing agent output",
                agent_type=agent_type,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            # Don't raise exception for storage failures - it's not critical for agent execution
        except Exception as e:
            self.logger.exception(
                "Unexpected error storing agent output",
                agent_type=agent_type,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            # Don't raise exception for storage failures - it's not critical for agent execution

    async def health_check(self) -> dict[str, Any]:
        """Check vector database connectivity."""
        try:
            if not self.client:
                await self.initialize()

            collections = await self.client.get_collections()
            collection_exists = any(
                collection.name == self.collection_name
                for collection in collections.collections
            )

            return {
                "status": "healthy",
                "collection_exists": collection_exists,
                "collection_name": self.collection_name,
            }

        except (ConnectionError, TimeoutError):
            self.logger.error("Vector health check connection failed")
            return {
                "status": "unhealthy",
                "collection_name": self.collection_name,
                "error": "connection_failed",
            }
        except (ValueError, KeyError, TypeError):
            self.logger.error("Vector health check validation failed")
            return {
                "status": "unhealthy",
                "collection_name": self.collection_name,
                "error": "validation_failed",
            }
        except Exception:
            self.logger.exception("Vector health check failed unexpectedly")
            return {
                "status": "unhealthy",
                "collection_name": self.collection_name,
                "error": "unexpected_error",
            }


# Global vector context retriever instance
vector_context = VectorContextRetriever()
