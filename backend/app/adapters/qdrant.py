"""Qdrant vector database adapter with multi-tenancy support."""

from __future__ import annotations

import asyncio
from datetime import UTC
from typing import Any, cast

import requests
from qdrant_client import QdrantClient
from qdrant_client.http import exceptions as qdrant_exceptions
from qdrant_client.http.models import (
    Condition,
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    KeywordIndexParams,
    KeywordIndexType,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.core.logger import LoggerMixin, get_logger
from app.schemas.vector import DocumentType, VisibilityLevel

logger = get_logger(__name__)


class QdrantAdapter(LoggerMixin):
    """Qdrant vector database adapter with multi-tenancy support"""

    def __init__(self) -> None:
        super().__init__()
        self.collection_name = settings.QDRANT_COLLECTION
        self.client: QdrantClient = self._initialize_client()

    def _initialize_client(self) -> QdrantClient:
        """Initialize Qdrant client connection"""
        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=30,
        )
        logger.info("Qdrant client initialized", url=settings.QDRANT_URL)
        return client

    async def health_check(self) -> dict[str, Any]:
        """Check Qdrant service health"""
        try:
            collections = await asyncio.get_running_loop().run_in_executor(
                None, self.client.get_collections
            )
        except qdrant_exceptions.ApiException as exc:
            logger.error("Qdrant API health check failed", error=str(exc))
            return {
                "status": "unhealthy",
                "message": "Qdrant API responded with an error",
                "details": {"error": str(exc)},
            }
        except (
            qdrant_exceptions.UnexpectedResponse,
            requests.exceptions.RequestException,
        ) as exc:
            logger.error("Qdrant connectivity health check failed", error=str(exc))
            return {
                "status": "unhealthy",
                "message": "Qdrant connection failed",
                "details": {"error": str(exc)},
            }

        return {
            "status": "healthy",
            "message": "Qdrant connection successful",
            "details": {
                "url": settings.QDRANT_URL,
                "collection_count": len(collections.collections),
            },
        }

    async def ensure_collection_exists(self) -> None:
        """Ensure the collection exists with proper configuration"""
        try:
            # Check if collection exists
            if self.client.collection_exists(self.collection_name):
                logger.info(
                    "Collection already exists", collection=self.collection_name
                )
                return

            # Get optimized HNSW configuration for multi-tenancy
            from app.core.hnsw_config import hnsw_configurator

            hnsw_config = hnsw_configurator.get_optimized_config_for_tenant_isolation()
            # Keep only supported keys for Qdrant
            _supported = {
                "m",
                "ef_construct",
                "ef",
                "full_scan_threshold",
                "max_indexing_threads",
            }
            hnsw_config_sanitized = {
                k: v for k, v in hnsw_config.items() if k in _supported
            }

            # Create collection with multi-tenancy optimized configuration
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI embedding size
                    distance=Distance.COSINE,
                ),
                hnsw_config=hnsw_config_sanitized,
                optimizers_config={
                    "deleted_threshold": 0.2,
                    "vacuum_min_vector_number": 1000,
                    "default_segment_number": 2,
                    "max_segment_size": None,
                    "memmap_threshold": 50000,
                    "indexing_threshold": 10000,
                },
            )

            logger.info(
                "Collection created with optimized HNSW config",
                hnsw_config=hnsw_configurator.get_configuration_summary(hnsw_config),
            )

            # Create payload indexes for multi-tenant filtering
            keyword_schema = KeywordIndexParams(type=KeywordIndexType.KEYWORD)
            payload_fields = [
                "tenant_id",
                "project_id",
                "type",
                "visibility",
                "lang",
                "version",
            ]

            for field_name in payload_fields:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=keyword_schema,
                    )
                    logger.info("Created payload index", field=field_name)
                except qdrant_exceptions.ApiException as exc:
                    logger.warning(
                        "Failed to create payload index",
                        field=field_name,
                        error=str(exc),
                    )

            logger.info(
                "Collection created successfully", collection=self.collection_name
            )

        except qdrant_exceptions.ApiException as e:
            logger.error(
                "Failed to create collection",
                error=str(e),
                collection=self.collection_name,
            )
            raise

    async def upsert_points(
        self,
        tenant_id: str,
        project_id: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        doc_type: str | DocumentType = "knowledge",
        visibility: str | VisibilityLevel = "private",
        version: str | None = "1.0",
        lang: str | None = "en",
    ) -> dict[str, Any]:
        """
        Upsert vector points with tenant and project isolation.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            vectors: List of embedding vectors
            payloads: List of payload dictionaries
            doc_type: Type of document ('knowledge' or 'memory')
            visibility: Document visibility ('private' or 'public')
            version: Document version
            lang: Document language (ISO 639-1)
        """
        try:
            await self.ensure_collection_exists()

            if len(vectors) != len(payloads):
                raise ValueError("vectors and payloads must have the same length")
            enriched_payloads: list[dict[str, Any]] = []
            for i, (_vector, payload) in enumerate(zip(vectors, payloads, strict=True)):
                doc_type_str = (
                    doc_type.value
                    if isinstance(doc_type, DocumentType)
                    else str(doc_type)
                )
                visibility_str = (
                    visibility.value
                    if isinstance(visibility, VisibilityLevel)
                    else str(visibility)
                )
                version_str = str(version) if version is not None else version
                lang_str = str(lang) if lang is not None else lang

                enriched_payload = {
                    **payload,
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "type": doc_type_str,
                    "visibility": visibility_str,
                    "version": version_str,
                    "lang": lang_str,
                    "created_at": self._get_current_timestamp(),
                    "vector_index": i,
                }
                enriched_payloads.append(enriched_payload)

            import uuid

            points = [
                PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)
                for vector, payload in zip(vectors, enriched_payloads, strict=True)
            ]

            loop = asyncio.get_running_loop()
            operation_info = await loop.run_in_executor(
                None,
                lambda: self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=True,
                ),
            )

            logger.info(
                "Points upserted successfully",
                tenant_id=tenant_id,
                project_id=project_id,
                doc_type=doc_type,
                count=len(points),
            )

            return {
                "status": "success",
                "points_count": len(points),
                "operation_id": getattr(operation_info, "operation_id", None),
                "doc_type": doc_type_str,
                "visibility": visibility_str,
            }

        except qdrant_exceptions.ApiException as exc:
            logger.error(
                "Qdrant API error while upserting points",
                error=str(exc),
                tenant_id=tenant_id,
                project_id=project_id,
            )
            raise
        except (
            qdrant_exceptions.UnexpectedResponse,
            requests.exceptions.RequestException,
        ) as exc:
            logger.error(
                "Qdrant connectivity error while upserting points",
                error=str(exc),
                tenant_id=tenant_id,
                project_id=project_id,
            )
            raise

    async def search(
        self,
        tenant_id: str,
        project_id: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search vectors with strict tenant and project isolation.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Additional search filters
        """
        try:
            await self.ensure_collection_exists()

            # Build mandatory tenant and project filter
            must_conditions: list[Condition] = [
                cast(
                    Condition,
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                ),
                cast(
                    Condition,
                    FieldCondition(
                        key="project_id", match=MatchValue(value=project_id)
                    ),
                ),
            ]

            # Add additional filters if provided
            if filters:
                for field, value in filters.items():
                    must_conditions.append(
                        cast(
                            Condition,
                            FieldCondition(key=field, match=MatchValue(value=value)),
                        )
                    )

            search_filter = Filter(must=must_conditions)

            loop = asyncio.get_running_loop()
            search_result = await loop.run_in_executor(
                None,
                lambda: self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=search_filter,
                    score_threshold=score_threshold,
                    with_payload=True,
                    with_vectors=False,
                ),
            )

            # Format results
            results = []
            for scored_point in search_result:
                results.append(
                    {
                        "id": scored_point.id,
                        "score": scored_point.score,
                        "payload": scored_point.payload,
                    }
                )

            logger.info(
                "Search completed",
                tenant_id=tenant_id,
                project_id=project_id,
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error(
                "Search failed",
                error=str(e),
                tenant_id=tenant_id,
                project_id=project_id,
            )
            raise

    async def delete_points(
        self, tenant_id: str, project_id: str, point_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Delete points by tenant/project or specific point IDs.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            point_ids: Specific point IDs to delete (optional)
        """
        try:
            await self.ensure_collection_exists()

            loop = asyncio.get_running_loop()

            if point_ids:
                # Delete specific points
                point_selector = PointIdsList(
                    points=[cast(int | str, pid) for pid in point_ids]
                )
                await loop.run_in_executor(
                    None,
                    lambda: self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=point_selector,
                        wait=True,
                    ),
                )
                logger.info(
                    "Specific points deleted",
                    tenant_id=tenant_id,
                    project_id=project_id,
                    count=len(point_ids),
                )
            else:
                # Delete all points for tenant/project
                delete_filter = Filter(
                    must=[
                        cast(
                            Condition,
                            FieldCondition(
                                key="tenant_id", match=MatchValue(value=tenant_id)
                            ),
                        ),
                        cast(
                            Condition,
                            FieldCondition(
                                key="project_id", match=MatchValue(value=project_id)
                            ),
                        ),
                    ]
                )

                await loop.run_in_executor(
                    None,
                    lambda: self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=FilterSelector(filter=delete_filter),
                        wait=True,
                    ),
                )
                logger.info(
                    "All project points deleted",
                    tenant_id=tenant_id,
                    project_id=project_id,
                )

            return {"status": "success", "message": "Points deleted successfully"}

        except Exception as e:
            logger.error(
                "Failed to delete points",
                error=str(e),
                tenant_id=tenant_id,
                project_id=project_id,
            )
            raise

    async def get_collection_stats(
        self, tenant_id: str | None = None, project_id: str | None = None
    ) -> dict[str, Any]:
        """Get collection statistics with optional filtering"""
        try:
            collection_info = self.client.get_collection(self.collection_name)

            vectors_config = collection_info.config.params.vectors
            if isinstance(vectors_config, dict):
                first_vector = next(iter(vectors_config.values()), None)
            else:
                first_vector = vectors_config

            vector_size = getattr(first_vector, "size", None)
            vector_distance = getattr(first_vector, "distance", None)

            base_stats: dict[str, Any] = {
                "vectors_count": collection_info.points_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "collection_status": collection_info.status,
                "collection_config": {
                    "vector_size": vector_size,
                    "distance": vector_distance,
                },
            }

            if tenant_id and project_id:
                # Get filtered stats for specific tenant/project
                count_filter = Filter(
                    must=[
                        cast(
                            Condition,
                            FieldCondition(
                                key="tenant_id", match=MatchValue(value=tenant_id)
                            ),
                        ),
                        cast(
                            Condition,
                            FieldCondition(
                                key="project_id", match=MatchValue(value=project_id)
                            ),
                        ),
                    ]
                )
                filter_stats = self.client.count(
                    collection_name=self.collection_name,
                    filter=count_filter,
                )
                base_stats["tenant_project_points"] = filter_stats.count

            return base_stats

        except Exception as e:
            logger.error("Failed to get collection stats", error=str(e))
            raise

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime

        return datetime.now(UTC).isoformat()
