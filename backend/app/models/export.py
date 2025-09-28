"""Export tracking model with multi-tenant support."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKeyConstraint, Index, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .project import Project


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
    status: Mapped[ExportStatus] = mapped_column(
        SQLEnum(ExportStatus, name="exportstatus", native_enum=False),
        default=ExportStatus.PENDING,
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Export manifest (list of included documents)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Error information
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Expiration (default 24 hours)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC) + timedelta(hours=24),
        nullable=False,
    )

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="exports",
        primaryjoin=(
            "and_(Export.project_id==Project.id, Export.tenant_id==Project.tenant_id)"
        ),
        foreign_keys=lambda: [Export.project_id, Export.tenant_id],
    )

    # User who requested the export
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    @property
    def is_expired(self) -> bool:
        """Check if export has expired."""
        return bool(datetime.now(UTC) > self.expires_at)

    @property
    def is_downloadable(self) -> bool:
        """Check if export is ready for download."""
        return bool(
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
