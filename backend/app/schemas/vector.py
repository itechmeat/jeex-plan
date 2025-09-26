"""
Vector database payload schemas for multi-tenant Qdrant implementation.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Types of documents stored in vector database"""
    KNOWLEDGE = "knowledge"  # Factual information from documents
    MEMORY = "memory"        # Contextual memory from agent interactions


class VisibilityLevel(str, Enum):
    """Document visibility levels"""
    PRIVATE = "private"      # Only accessible within tenant/project
    PUBLIC = "public"        # Accessible across projects (future feature)


class VectorPayload(BaseModel):
    """Standard payload structure for vector database entries"""

    # Required identification fields
    tenant_id: str = Field(..., description="Tenant identifier for isolation")
    project_id: str = Field(..., description="Project identifier for scoping")

    # Document metadata
    type: DocumentType = Field(default=DocumentType.KNOWLEDGE, description="Type of stored information")
    visibility: VisibilityLevel = Field(default=VisibilityLevel.PRIVATE, description="Access visibility level")
    version: str = Field(default="1.0", description="Document version")
    lang: str = Field(default="en", description="Content language (ISO 639-1)")

    # Content information
    content_type: str | None = Field(None, description="MIME type or content classification")
    source: str | None = Field(None, description="Source document or agent")
    chunk_index: int | None = Field(None, description="Index in chunked content")
    total_chunks: int | None = Field(None, description="Total chunks in source")

    # Search and filtering metadata
    tags: list[str] = Field(default_factory=list, description="Arbitrary tags for categorization")
    title: str | None = Field(None, description="Document or section title")
    section: str | None = Field(None, description="Document section name")

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")

    # Quality metrics
    confidence_score: float | None = Field(None, ge=0.0, le=1.0, description="Content confidence score")
    relevance_score: float | None = Field(None, ge=0.0, le=1.0, description="Search relevance score")

    # Technical metadata
    vector_index: int | None = Field(None, description="Index in batch upload")
    batch_id: str | None = Field(None, description="Batch upload identifier")
    embedding_model: str | None = Field(None, description="Model used for embedding")

    # Additional flexible metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Qdrant payload"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VectorPayload":
        """Create from dictionary payload"""
        return cls(**data)


class SearchResult(BaseModel):
    """Single search result from vector database"""
    id: str = Field(..., description="Point identifier")
    score: float = Field(..., description="Similarity score", ge=0.0, le=1.0)
    payload: VectorPayload = Field(..., description="Vector payload data")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "score": self.score,
            "payload": self.payload.to_dict()
        }


class SearchRequest(BaseModel):
    """Search request parameters"""
    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")
    query_vector: list[float] = Field(..., description="Query embedding vector")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")

    # Optional filters
    doc_types: list[DocumentType] | None = Field(None, description="Filter by document types")
    visibility: VisibilityLevel | None = Field(None, description="Filter by visibility")
    lang: str | None = Field(None, description="Filter by language")
    tags: list[str] | None = Field(None, description="Filter by tags")
    version: str | None = Field(None, description="Filter by version")

    # Search options
    include_vectors: bool = Field(default=False, description="Include vector data in results")
    with_payload: bool = Field(default=True, description="Include payload data")


class UpsertRequest(BaseModel):
    """Bulk upsert request parameters"""
    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")
    vectors: list[list[float]] = Field(..., description="List of embedding vectors")
    payloads: list[dict[str, Any]] = Field(..., description="List of payload dictionaries")
    doc_type: DocumentType = Field(default=DocumentType.KNOWLEDGE, description="Document type")
    visibility: VisibilityLevel = Field(default=VisibilityLevel.PRIVATE, description="Visibility level")
    version: str = Field(default="1.0", description="Document version")
    lang: str = Field(default="en", description="Content language")

    def validate_vectors_payloads(self) -> bool:
        """Validate that vectors and payloads match"""
        return len(self.vectors) == len(self.payloads)

    def enrich_payloads(self) -> list[VectorPayload]:
        """Add common fields to all payloads"""
        enriched = []
        for i, payload in enumerate(self.payloads):
            base_payload = VectorPayload(
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                type=self.doc_type,
                visibility=self.visibility,
                version=self.version,
                lang=self.lang,
                vector_index=i,
                **payload
            )
            enriched.append(base_payload)
        return enriched


class DeleteRequest(BaseModel):
    """Delete request parameters"""
    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")

    # Optional specific filters
    point_ids: list[str] | None = Field(None, description="Specific point IDs to delete")
    doc_types: list[DocumentType] | None = Field(None, description="Filter by document types")
    version: str | None = Field(None, description="Filter by version")

    def get_filter_conditions(self) -> dict[str, Any]:
        """Build filter conditions for deletion"""
        conditions = {
            "must": [
                {"key": "tenant_id", "match": {"value": self.tenant_id}},
                {"key": "project_id", "match": {"value": self.project_id}}
            ]
        }

        if self.doc_types:
            conditions["must"].extend([
                {"key": "type", "match": {"value": doc_type.value}}
                for doc_type in self.doc_types
            ])

        if self.version:
            conditions["must"].append({
                "key": "version", "match": {"value": self.version}
            })

        return conditions


class CollectionStats(BaseModel):
    """Collection statistics"""
    vectors_count: int = Field(..., description="Total vectors in collection")
    indexed_vectors_count: int = Field(..., description="Indexed vectors count")
    collection_status: str = Field(..., description="Collection status")
    tenant_project_points: int | None = Field(None, description="Points for specific tenant/project")
    collection_config: dict[str, Any] = Field(..., description="Collection configuration")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(exclude_none=True)
