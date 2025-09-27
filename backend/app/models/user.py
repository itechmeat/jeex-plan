"""User model with multi-tenant support."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .project import Project
    from .rbac import ProjectMember
    from .tenant import Tenant


class User(BaseModel):
    """User entity with tenant association."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Null for OAuth-only users
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Session tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # OAuth fields
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Explicit tenant foreign key (inherited tenant_id from TenantMixin needs FK)
    tenant: Mapped[Tenant] = relationship(
        "Tenant", back_populates="users", foreign_keys="User.tenant_id"
    )

    # Projects relationship
    projects: Mapped[list[Project]] = relationship("Project", back_populates="owner")
    project_memberships: Mapped[list[ProjectMember]] = relationship(
        "ProjectMember", foreign_keys="ProjectMember.user_id", back_populates="user"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
        UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),
    )

    class Config:
        """Pydantic config."""

        from_attributes = True
