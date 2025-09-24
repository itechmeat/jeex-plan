"""
Qdrant vector database service.
Handles vector storage, search, and multi-tenant isolation.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    VectorParams, Distance, HnswConfigDiff,
    Filter, FieldCondition, MatchValue, PointStruct, ScoredPoint
)

from app.core.config import settings
from app.services.embedding import EmbeddingService
from app.core.logger import get_logger

logger = get_logger()


class QdrantService:
    """Service for vector database operations with multi-tenant support."""

    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        self.collection_name = settings.QDRANT_COLLECTION
        self.embedding_service = EmbeddingService()
        self._collection_initialized = False

    async def initialize(self) -> None:
        """Initialize Qdrant collection with proper configuration."""
        if self._collection_initialized:
            return

        try:
            # Check if collection exists
            collections = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_collections
            )
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection with multi-tenant optimized HNSW config
                await asyncio.get_event_loop().run_in_executor(
                    None, self._create_collection
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection already exists: {self.collection_name}")

            self._collection_initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise

    def _create_collection(self) -> None:
        """Create Qdrant collection with optimized settings."""
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=1536,  # OpenAI text-embedding-3-small dimension
                distance=Distance.COSINE
            ),
            hnsw_config=HnswConfigDiff(
                m=0,  # Disable global graph for multi-tenant optimization
                payload_m=16  # Create payload-specific connections
            )
        )

        # Create payload indexes for efficient filtering
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="tenant_id",
            field_schema=models.KeywordIndexParams()
        )
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="project_id",
            field_schema=models.KeywordIndexParams()
        )
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="type",
            field_schema=models.KeywordIndexParams()
        )

    def _create_tenant_filter(self, tenant_id: str, project_id: str) -> Filter:
        """Create filter for tenant and project isolation."""
        return Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                ),
                FieldCondition(
                    key="project_id",
                    match=MatchValue(value=project_id)
                )
            ]
        )

    async def upsert_documents(
        self,
        documents: List[str],
        metadata_list: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Upsert documents with embeddings into Qdrant."""
        await self.initialize()

        if len(documents) != len(metadata_list):
            raise ValueError("Documents and metadata lists must have the same length")

        if not documents:
            return []

        try:
            # Generate embeddings
            embeddings = await self.embedding_service.embed_texts(documents)

            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid4()) for _ in documents]

            # Validate metadata has required fields
            required_fields = {"tenant_id", "project_id", "type"}
            for i, metadata in enumerate(metadata_list):
                missing_fields = required_fields - set(metadata.keys())
                if missing_fields:
                    raise ValueError(
                        f"Metadata item {i} missing required fields: {missing_fields}"
                    )

            # Create points
            points = []
            for i, (doc, embedding, metadata) in enumerate(zip(documents, embeddings, metadata_list)):
                # Add document content to metadata
                full_metadata = {
                    **metadata,
                    "content": doc,
                    "lang": metadata.get("lang", "en"),
                    "version": metadata.get("version", "1"),
                    "visibility": metadata.get("visibility", "private"),
                    "tags": metadata.get("tags", [])
                }

                point = PointStruct(
                    id=ids[i],
                    vector=embedding,
                    payload=full_metadata
                )
                points.append(point)

            # Upsert points
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.upsert,
                self.collection_name, points
            )

            logger.info(f"Upserted {len(points)} documents to Qdrant")
            return ids

        except Exception as e:
            logger.error(f"Failed to upsert documents to Qdrant: {e}")
            raise

    async def search_documents(
        self,
        query: str,
        tenant_id: str,
        project_id: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        document_type: Optional[str] = None,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        """Search documents with tenant and project isolation."""
        await self.initialize()

        try:
            # Generate query embedding
            query_embeddings = await self.embedding_service.embed_texts([query])
            query_vector = query_embeddings[0]

            # Create base filter
            filter_conditions = [
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                FieldCondition(key="project_id", match=MatchValue(value=project_id))
            ]

            # Add document type filter if specified
            if document_type:
                filter_conditions.append(
                    FieldCondition(key="document_type", match=MatchValue(value=document_type))
                )

            # Add additional filters
            if additional_filters:
                for key, value in additional_filters.items():
                    filter_conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )

            search_filter = Filter(must=filter_conditions)

            # Search
            search_result = await asyncio.get_event_loop().run_in_executor(
                None, self.client.search,
                self.collection_name, query_vector, search_filter, limit, True
            )

            # Filter by score threshold and format results
            results = []
            for point in search_result:
                if point.score >= score_threshold:
                    content = point.payload.get("content", "")
                    metadata = {k: v for k, v in point.payload.items() if k != "content"}
                    results.append((content, metadata, point.score))

            logger.info(f"Found {len(results)} matching documents")
            return results

        except Exception as e:
            logger.error(f"Failed to search documents in Qdrant: {e}")
            raise

    async def get_document_context(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        max_context_length: int = 4000,
        score_threshold: float = 0.7
    ) -> str:
        """Get relevant document context for a query."""
        try:
            search_results = await self.search_documents(
                query=query,
                tenant_id=tenant_id,
                project_id=project_id,
                limit=20,
                score_threshold=score_threshold
            )

            if not search_results:
                return ""

            # Combine relevant content with length limit
            context_parts = []
            total_length = 0

            for content, metadata, score in search_results:
                # Add document type and score info
                doc_info = f"[{metadata.get('document_type', 'unknown')} - score: {score:.2f}]"
                full_content = f"{doc_info}\n{content}\n"

                if total_length + len(full_content) > max_context_length:
                    # Add partial content if there's space
                    remaining_space = max_context_length - total_length - len(doc_info) - 10
                    if remaining_space > 100:  # Only add if meaningful space
                        partial_content = f"{doc_info}\n{content[:remaining_space]}...\n"
                        context_parts.append(partial_content)
                    break

                context_parts.append(full_content)
                total_length += len(full_content)

            return "\n---\n".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to get document context: {e}")
            return ""

    async def delete_project_documents(self, tenant_id: str, project_id: str) -> None:
        """Delete all documents for a project."""
        await self.initialize()

        try:
            # Create filter for project documents
            project_filter = self._create_tenant_filter(tenant_id, project_id)

            # Delete points
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.delete,
                self.collection_name, models.FilterSelector(filter=project_filter)
            )

            logger.info(f"Deleted all documents for project {project_id}")

        except Exception as e:
            logger.error(f"Failed to delete project documents: {e}")
            raise

    async def delete_document_version(
        self,
        tenant_id: str,
        project_id: str,
        document_id: str
    ) -> None:
        """Delete specific document version."""
        await self.initialize()

        try:
            # Create filter for specific document
            document_filter = Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                    FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                ]
            )

            # Delete points
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.delete,
                self.collection_name, models.FilterSelector(filter=document_filter)
            )

            logger.info(f"Deleted document {document_id}")

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        await self.initialize()

        try:
            info = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_collection,
                self.collection_name
            )

            return {
                "total_points": info.points_count,
                "indexed_points": info.indexed_vectors_count,
                "status": info.status.value,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.value,
                    "hnsw_m": info.config.hnsw_config.m,
                    "hnsw_payload_m": info.config.hnsw_config.payload_m
                }
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check Qdrant service health."""
        try:
            await self.initialize()
            stats = await self.get_collection_stats()

            return {
                "status": "healthy",
                "collection": self.collection_name,
                "stats": stats
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "collection": self.collection_name
            }