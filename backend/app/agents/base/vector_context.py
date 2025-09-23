"""
Vector context retrieval for agents.
Integrates with Qdrant for project-specific knowledge retrieval.
"""

from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime, timezone

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.core.logger import get_logger
from ..contracts.base import ProjectContext, ContextRetrievalError

logger = get_logger()


class VectorContextRetriever:
    """Retrieves relevant context from vector database."""

    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
        self.collection_name = settings.QDRANT_COLLECTION
        self.logger = get_logger("vector_context")

    async def initialize(self):
        """Initialize Qdrant client."""
        try:
            self.client = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
            self.logger.info("Vector context retriever initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant client: {e}")
            raise

    async def get_project_context(
        self,
        context: ProjectContext,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Retrieve relevant context for a project."""
        if not self.client:
            await self.initialize()

        try:
            # Create filter for tenant and project isolation
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=context.tenant_id)
                    ),
                    FieldCondition(
                        key="project_id",
                        match=MatchValue(value=context.project_id)
                    ),
                ]
            )

            # Perform vector search
            search_results = await self.client.search(
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
                payload = result.payload
                document_data = {
                    "content": payload.get("text", ""),
                    "type": payload.get("type", "unknown"),
                    "version": payload.get("version", "1"),
                    "score": result.score,
                    "metadata": {
                        k: v for k, v in payload.items()
                        if k not in ["text", "type", "version", "tenant_id", "project_id"]
                    }
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

        except Exception as e:
            self.logger.error(
                "Failed to retrieve project context",
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            raise ContextRetrievalError(
                message=f"Vector context retrieval failed: {str(e)}",
                agent_type="vector_context",
                correlation_id=context.correlation_id,
                details={"query": query, "error": str(e)},
            )

    async def get_step_context(
        self,
        context: ProjectContext,
        step: int,
        limit: int = 5,
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Store agent output in vector database for future context."""
        if not self.client:
            await self.initialize()

        try:
            payload = {
                "tenant_id": context.tenant_id,
                "project_id": context.project_id,
                "type": "memory",
                "agent_type": agent_type,
                "step": context.current_step,
                "text": content,
                "version": "1",
                "lang": context.language,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            }

            # Generate embedding and store
            await self.client.add(
                collection_name=self.collection_name,
                documents=[content],
                metadata=[payload],
            )

            self.logger.info(
                "Stored agent output in vector database",
                agent_type=agent_type,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                content_length=len(content),
            )

        except Exception as e:
            self.logger.error(
                "Failed to store agent output",
                agent_type=agent_type,
                tenant_id=context.tenant_id,
                project_id=context.project_id,
                correlation_id=context.correlation_id,
                error=str(e),
            )
            # Don't raise exception for storage failures - it's not critical for agent execution

    async def health_check(self) -> Dict[str, Any]:
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

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "collection_name": self.collection_name,
            }


# Global vector context retriever instance
vector_context = VectorContextRetriever()