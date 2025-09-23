"""
Qdrant vector database adapter with multi-tenancy support.
"""

from typing import List, Dict, Any, Optional, Union
from app.schemas.vector import DocumentType, VisibilityLevel
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    CreateCollection,
    CollectionInfo
)

from app.core.config import settings
from app.core.logger import get_logger, LoggerMixin

logger = get_logger(__name__)


class QdrantAdapter(LoggerMixin):
    """Qdrant vector database adapter with multi-tenancy support"""

    def __init__(self):
        super().__init__()
        self.client = None
        self.collection_name = settings.QDRANT_COLLECTION
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Qdrant client connection"""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=30
            )
            logger.info("Qdrant client initialized", url=settings.QDRANT_URL)
        except Exception as e:
            logger.error("Failed to initialize Qdrant client", error=str(e))
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check Qdrant service health"""
        try:
            # Test basic connectivity
            collections = self.client.get_collections()
            return {
                "status": "healthy",
                "message": "Qdrant connection successful",
                "details": {
                    "url": settings.QDRANT_URL,
                    "collection_count": len(collections.collections),
                    "version": "1.15.4"
                }
            }
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"Qdrant connection failed: {str(e)}",
                "details": {"error": str(e)}
            }

    async def ensure_collection_exists(self):
        """Ensure the collection exists with proper configuration"""
        try:
            # Check if collection exists
            try:
                collection_info = self.client.get_collection(self.collection_name)
                logger.info("Collection already exists", collection=self.collection_name)
                return
            except Exception:
                # Collection doesn't exist, create it
                pass

            # Get optimized HNSW configuration for multi-tenancy
            from app.core.hnsw_config import hnsw_configurator
            hnsw_config = hnsw_configurator.get_optimized_config_for_tenant_isolation()
            # Keep only supported keys for Qdrant
            _supported = {"m", "ef_construct", "ef", "full_scan_threshold", "max_indexing_threads"}
            hnsw_config_sanitized = {k: v for k, v in hnsw_config.items() if k in _supported}

            # Create collection with multi-tenancy optimized configuration
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI embedding size
                    distance=Distance.COSINE
                ),
                hnsw_config=hnsw_config_sanitized,
                optimizers_config={
                    "deleted_threshold": 0.2,
                    "vacuum_min_vector_number": 1000,
                    "default_segment_number": 2,
                    "max_segment_size": None,
                    "memmap_threshold": 50000,
                    "indexing_threshold": 10000
                }
            )

            logger.info(
                "Collection created with optimized HNSW config",
                hnsw_config=hnsw_configurator.get_configuration_summary(hnsw_config)
            )

            # Create payload indexes for multi-tenant filtering
            payload_fields = [
                ("tenant_id", "keyword"),
                ("project_id", "keyword"),
                ("type", "keyword"),
                ("visibility", "keyword"),
                ("lang", "keyword"),
                ("version", "keyword")
            ]

            for field_name, field_schema in payload_fields:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_schema
                    )
                    logger.info("Created payload index", field=field_name)
                except Exception as index_error:
                    logger.warning(
                        "Failed to create payload index",
                        field=field_name,
                        error=str(index_error)
                    )

            logger.info("Collection created successfully", collection=self.collection_name)

        except Exception as e:
            logger.error("Failed to create collection", error=str(e))
            raise

    async def upsert_points(
        self,
        tenant_id: str,
        project_id: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        doc_type: Union[str, "DocumentType"] = "knowledge",
        visibility: Union[str, "VisibilityLevel"] = "private",
        version: Union[str, None] = "1.0",
        lang: Union[str, None] = "en"
    ) -> Dict[str, Any]:
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

            # Add tenant and project context to all payloads
            enriched_payloads = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads)):
                # Convert enum values to strings for JSON serialization
                doc_type_str = doc_type.value if hasattr(doc_type, 'value') else str(doc_type)
                visibility_str = visibility.value if hasattr(visibility, 'value') else str(visibility)
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
                    "vector_index": i
                }
                enriched_payloads.append(enriched_payload)

            # Create point structures with UUID-style IDs
            import uuid
            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload
                )
                for i, (vector, payload) in enumerate(zip(vectors, enriched_payloads))
            ]

            # Upsert points
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )

            logger.info(
                "Points upserted successfully",
                tenant_id=tenant_id,
                project_id=project_id,
                doc_type=doc_type,
                count=len(points)
            )

            return {
                "status": "success",
                "points_count": len(points),
                "operation_id": operation_info.operation_id,
                "doc_type": doc_type,
                "visibility": visibility
            }

        except Exception as e:
            logger.error(
                "Failed to upsert points",
                error=str(e),
                tenant_id=tenant_id,
                project_id=project_id
            )
            raise

    async def search(
        self,
        tenant_id: str,
        project_id: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
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
            must_conditions = [
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                FieldCondition(key="project_id", match=MatchValue(value=project_id))
            ]

            # Add additional filters if provided
            if filters:
                for field, value in filters.items():
                    must_conditions.append(
                        FieldCondition(key=field, match=MatchValue(value=value))
                    )

            search_filter = Filter(must=must_conditions)

            # Perform search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=search_filter,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False
            )

            # Format results
            results = []
            for scored_point in search_result:
                results.append({
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "payload": scored_point.payload
                })

            logger.info(
                "Search completed",
                tenant_id=tenant_id,
                project_id=project_id,
                results_count=len(results)
            )

            return results

        except Exception as e:
            logger.error(
                "Search failed",
                error=str(e),
                tenant_id=tenant_id,
                project_id=project_id
            )
            raise

    async def delete_points(
        self,
        tenant_id: str,
        project_id: str,
        point_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Delete points by tenant/project or specific point IDs.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            point_ids: Specific point IDs to delete (optional)
        """
        try:
            await self.ensure_collection_exists()

            if point_ids:
                # Delete specific points
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids,
                    wait=True
                )
                logger.info(
                    "Specific points deleted",
                    tenant_id=tenant_id,
                    project_id=project_id,
                    count=len(point_ids)
                )
            else:
                # Delete all points for tenant/project
                delete_filter = Filter(
                    must=[
                        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                        FieldCondition(key="project_id", match=MatchValue(value=project_id))
                    ]
                )

                self.client.delete(
                    collection_name=self.collection_name,
                    filter=delete_filter,
                    wait=True
                )
                logger.info(
                    "All project points deleted",
                    tenant_id=tenant_id,
                    project_id=project_id
                )

            return {"status": "success", "message": "Points deleted successfully"}

        except Exception as e:
            logger.error(
                "Failed to delete points",
                error=str(e),
                tenant_id=tenant_id,
                project_id=project_id
            )
            raise

    async def get_collection_stats(self, tenant_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """Get collection statistics with optional filtering"""
        try:
            collection_info = self.client.get_collection(self.collection_name)

            base_stats = {
                "vectors_count": collection_info.points_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "collection_status": collection_info.status,
                "collection_config": {
                    "vector_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance
                }
            }

            if tenant_id and project_id:
                # Get filtered stats for specific tenant/project
                filter_stats = self.client.count(
                    collection_name=self.collection_name,
                    filter=Filter(
                        must=[
                            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                            FieldCondition(key="project_id", match=MatchValue(value=project_id))
                        ]
                    )
                )
                base_stats["tenant_project_points"] = filter_stats.count

            return base_stats

        except Exception as e:
            logger.error("Failed to get collection stats", error=str(e))
            raise

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()