"""
Vector database API endpoints with strict tenant isolation.

Provides endpoints for document storage, semantic search, and vector management
with automatic tenant/project scoping and server-side filtering.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.adapters.qdrant import QdrantAdapter
from app.core.logger import get_logger
from app.middleware.tenant_filter import VectorOperationFilter
from app.schemas.vector import (
    CollectionStats,
    DeleteRequest,
    DocumentType,
    SearchRequest,
    SearchResult,
    UpsertRequest,
    VectorPayload,
    VisibilityLevel,
)
from app.services.embedding import ChunkingStrategy, EmbeddingService, TextNormalization

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/vectors", tags=["vectors"])

# Initialize services
qdrant_adapter = QdrantAdapter()
embedding_service = EmbeddingService()


async def get_tenant_context(request: Request) -> dict[str, str]:
    """Extract tenant context from request state (set by middleware)"""
    if not hasattr(request.state, 'tenant_context'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant context"
        )
    return request.state.tenant_context


@router.post("/search", response_model=list[SearchResult])
async def search_vectors(
    request: SearchRequest,
    http_request: Request
) -> list[SearchResult]:
    """
    Search vectors with strict tenant/project isolation.

    Performs semantic search within the tenant and project scope only.
    Server-side filtering prevents cross-tenant data access.
    """
    try:
        # Get tenant context from middleware
        tenant_context = await get_tenant_context(http_request)

        # Validate that request matches tenant context
        if (request.tenant_id != tenant_context["tenant_id"] or
            request.project_id != tenant_context["project_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant/project context mismatch"
            )

        # Build search filter with tenant isolation
        additional_filters = {}
        if request.doc_types:
            additional_filters["doc_types"] = [dt.value for dt in request.doc_types]
        if request.visibility:
            additional_filters["visibility"] = request.visibility.value
        if request.lang:
            additional_filters["lang"] = request.lang
        if request.tags:
            additional_filters["tags"] = request.tags
        if request.version:
            additional_filters["version"] = request.version

        VectorOperationFilter.build_search_filter(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            additional_filters=additional_filters
        )

        # Perform search
        search_results = await qdrant_adapter.search(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            query_vector=request.query_vector,
            limit=request.limit,
            score_threshold=request.score_threshold,
            filters=additional_filters
        )

        # Convert results to response format
        results = []
        for result in search_results:
            payload = VectorPayload.from_dict(result["payload"])
            search_result = SearchResult(
                id=result["id"],
                score=result["score"],
                payload=payload
            )
            results.append(search_result)

        logger.info(
            "Vector search completed",
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            results_count=len(results),
            score_threshold=request.score_threshold
        )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Vector search failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e!s}"
        )


@router.post("/upsert")
async def upsert_vectors(
    request: UpsertRequest,
    http_request: Request
) -> dict[str, Any]:
    """
    Bulk upsert pre-computed vectors with tenant isolation.

    Accepts pre-computed embedding vectors and payloads, validates them,
    enriches with metadata, and stores in Qdrant with strict tenant/project isolation.
    """
    try:
        # Get tenant context from middleware
        tenant_context = await get_tenant_context(http_request)

        # Validate that request matches tenant context
        if (request.tenant_id != tenant_context["tenant_id"] or
            request.project_id != tenant_context["project_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant/project context mismatch"
            )

        # Validate vectors and payloads are present
        if not request.vectors or not request.payloads:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vectors and payloads are required"
            )

        # Validate vectors and payloads match
        if not request.validate_vectors_payloads():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vectors and payloads count mismatch"
            )

        # Enrich payloads with metadata using schema method
        enriched_payloads = request.enrich_payloads()
        payload_dicts = [payload.to_dict() for payload in enriched_payloads]

        # Upsert vectors to Qdrant
        upsert_result = await qdrant_adapter.upsert_points(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            vectors=request.vectors,
            payloads=payload_dicts,
            doc_type=request.doc_type,
            visibility=request.visibility,
            version=request.version,
            lang=request.lang
        )

        response = {
            "status": "success",
            "message": "Vectors upserted successfully",
            "tenant_id": request.tenant_id,
            "project_id": request.project_id,
            "vectors_count": len(request.vectors),
            "payloads_count": len(request.payloads),
            "doc_type": request.doc_type,
            "visibility": request.visibility,
            "version": request.version,
            "lang": request.lang,
            "upsert_operation": upsert_result
        }

        logger.info(
            "Vectors upserted successfully",
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            vectors_count=len(request.vectors),
            payloads_count=len(request.payloads)
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Vector upsert failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upsert failed: {e!s}"
        )


@router.post("/embed-and-store")
async def embed_and_store(
    text: str,
    tenant_id: str = Query(..., description="Tenant identifier"),
    project_id: str = Query(..., description="Project identifier"),
    doc_type: DocumentType = Query(DocumentType.KNOWLEDGE, description="Document type"),
    visibility: VisibilityLevel = Query(VisibilityLevel.PRIVATE, description="Visibility level"),
    version: str = Query("1.0", description="Document version"),
    lang: str = Query("en", description="Document language"),
    http_request: Request = None
) -> dict[str, Any]:
    """
    Simplified endpoint: process text and store embeddings in one call.

    This endpoint handles the complete pipeline from raw text to stored vectors
    with automatic tenant isolation and minimal required parameters.
    """
    try:
        # Get tenant context from middleware
        tenant_context = await get_tenant_context(http_request)

        # Validate that request matches tenant context
        if (tenant_id != tenant_context["tenant_id"] or
            project_id != tenant_context["project_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant/project context mismatch"
            )

        # Process text through embedding pipeline
        embedding_result = await embedding_service.process_document(
            text=text,
            doc_type=doc_type,
            chunking_strategy=ChunkingStrategy.PARAGRAPH,
            normalization=TextNormalization.STANDARD,
            metadata={"source": "api_upload", "lang": lang}
        )

        # Prepare payloads from chunks
        payloads = []
        for chunk in embedding_result.chunks:
            payload = {
                **chunk.metadata,
                "confidence_score": chunk.confidence_score,
                "total_chunks": len(embedding_result.chunks),
                "embedding_model": embedding_result.model_used,
                "content_type": "text/plain"
            }
            payloads.append(payload)

        # Upsert vectors to Qdrant
        await qdrant_adapter.upsert_points(
            tenant_id=tenant_id,
            project_id=project_id,
            vectors=embedding_result.embeddings,
            payloads=payloads,
            doc_type=doc_type,
            visibility=visibility,
            version=version,
            lang=lang
        )

        response = {
            "status": "success",
            "message": "Text embedded and stored successfully",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "doc_type": doc_type,
            "chunks_processed": len(embedding_result.chunks),
            "embedding_model": embedding_result.model_used,
            "processing_time_ms": embedding_result.processing_time_ms,
            "total_tokens": embedding_result.total_tokens,
            "deduplication_stats": embedding_result.deduplication_stats,
            "vector_dimensions": len(embedding_result.embeddings[0]) if embedding_result.embeddings else 0
        }

        logger.info(
            "Text embedded and stored successfully",
            tenant_id=tenant_id,
            project_id=project_id,
            chunks_count=len(embedding_result.chunks),
            processing_time_ms=embedding_result.processing_time_ms
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Embed and store failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embed and store failed: {e!s}"
        )


@router.delete("/delete")
async def delete_vectors(
    request: DeleteRequest,
    http_request: Request
) -> dict[str, Any]:
    """
    Delete vectors with tenant isolation and optional filtering.

    Can delete specific points or all vectors for a tenant/project.
    Server-side filtering ensures only authorized data is deleted.
    """
    try:
        # Get tenant context from middleware
        tenant_context = await get_tenant_context(http_request)

        # Validate that request matches tenant context
        if (request.tenant_id != tenant_context["tenant_id"] or
            request.project_id != tenant_context["project_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant/project context mismatch"
            )

        # Build delete filter
        if request.point_ids:
            # Delete specific points
            result = await qdrant_adapter.delete_points(
                tenant_id=request.tenant_id,
                project_id=request.project_id,
                point_ids=request.point_ids
            )
        else:
            # Delete by filter
            result = await qdrant_adapter.delete_points(
                tenant_id=request.tenant_id,
                project_id=request.project_id
            )

            # If additional filters specified, we need to use the filtered delete
            if request.doc_types or request.version:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Filtered delete is not implemented; omit filters or delete specific point_ids"
                )

        response = {
            "status": "success",
            "message": "Vectors deleted successfully",
            "tenant_id": request.tenant_id,
            "project_id": request.project_id,
            "delete_operation": result
        }

        logger.info(
            "Vectors deleted successfully",
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            point_ids_count=len(request.point_ids) if request.point_ids else 0
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Vector deletion failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Delete failed: {e!s}"
        )


@router.get("/stats", response_model=CollectionStats)
async def get_collection_stats(
    tenant_id: str = Query(..., description="Tenant identifier"),
    project_id: str = Query(..., description="Project identifier"),
    http_request: Request = None
) -> CollectionStats:
    """
    Get collection statistics with optional tenant/project filtering.

    Returns comprehensive statistics about the vector collection
    with optional filtering for specific tenant/project scope.
    """
    try:
        # Get tenant context from middleware
        tenant_context = await get_tenant_context(http_request)

        # Validate that request matches tenant context
        if (tenant_id != tenant_context["tenant_id"] or
            project_id != tenant_context["project_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant/project context mismatch"
            )

        # Get collection statistics
        stats = await qdrant_adapter.get_collection_stats(
            tenant_id=tenant_id,
            project_id=project_id
        )

        logger.info(
            "Collection stats retrieved",
            tenant_id=tenant_id,
            project_id=project_id,
            total_vectors=stats.get("vectors_count", 0),
            tenant_project_vectors=stats.get("tenant_project_points", 0)
        )

        return CollectionStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get collection stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stats retrieval failed: {e!s}"
        )


@router.get("/health")
async def vector_health_check() -> dict[str, Any]:
    """
    Health check for vector database operations.

    Returns status of Qdrant connection and embedding service.
    """
    try:
        # Check Qdrant health
        qdrant_health = await qdrant_adapter.health_check()

        # Check embedding service
        embedding_healthy = embedding_service._embedding_client is not None

        health_status = {
            "status": "healthy" if qdrant_health["status"] == "healthy" and embedding_healthy else "unhealthy",
            "services": {
                "qdrant": qdrant_health,
                "embedding_service": {
                    "status": "healthy" if embedding_healthy else "unhealthy",
                    "model": embedding_service.embedding_model
                }
            },
            "tenant_isolation": "enabled"
        }

        return health_status

    except Exception as e:
        logger.error("Vector health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "services": {
                "qdrant": {"status": "unhealthy", "error": str(e)},
                "embedding_service": {"status": "unknown"}
            }
        }
