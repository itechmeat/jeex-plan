"""
Export tracking model with multi-tenant support.
Handles ZIP archive generation and download management.
"""

from datetime import UTC, datetime, timedelta
from enum import Enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class ExportStatus(str, Enum):
    """Export status enumeration."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class Export(BaseModel):
    """Export tracking entity with tenant isolation."""

    __tablename__ = "exports"

    # Export info
    status = Column(String(50), default=ExportStatus.PENDING.value, nullable=False, index=True)
    file_path = Column(Text, nullable=True)

    # Export manifest (list of included documents)
    manifest = Column(JSON, default=dict, nullable=False)

    # Error information
    error_message = Column(Text, nullable=True)

    # Expiration (default 24 hours)
    expires_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC) + timedelta(hours=24),
        nullable=False,
        index=True
    )

    # Project relationship
    project_id = Column(UUID(as_uuid=True), nullable=False)
    project = relationship(
        "Project",
        back_populates="exports",
        primaryjoin="and_(Export.project_id==Project.id, Export.tenant_id==Project.tenant_id)",
        foreign_keys=[project_id]
    )

    # User who requested the export
    requested_by = Column(UUID(as_uuid=True), nullable=False)

    @property
    def is_expired(self) -> bool:
        """Check if export has expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_downloadable(self) -> bool:
        """Check if export is ready for download."""
        return (
            self.status == ExportStatus.COMPLETED.value
            and not self.is_expired
            and self.file_path is not None
        )

    __table_args__ = (
        # Tenant-scoped FK constraint
        ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            ondelete="CASCADE",
        ),
        Index("idx_exports_project", "project_id"),
        Index("idx_exports_expires", "expires_at"),
        Index("idx_exports_status", "status"),
        Index("idx_exports_tenant_created", "tenant_id", "created_at"),
    )
