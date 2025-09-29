"""Tenant model for multi-tenancy support."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .project import Project
    from .user import User


class Tenant(Base, TimestampMixin):
    """Tenant entity for multi-tenant architecture."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Configuration
    max_projects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_storage_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    users: Mapped[list[User]] = relationship("User", back_populates="tenant")
    projects: Mapped[list[Project]] = relationship(
        "Project", back_populates="tenant", overlaps="owner"
    )

    __table_args__ = (
        # Multi-column index for PostgreSQL 18 skip scans
        Index("idx_tenant_slug_active", "slug", "is_active"),
    )
