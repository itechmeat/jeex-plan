"""
User model with multi-tenant support.
"""

from sqlalchemy import Boolean, Column, DateTime, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import BaseModel


class User(BaseModel):
    """User entity with tenant association."""

    __tablename__ = "users"

    email = Column(String(255), nullable=False, index=True)
    username = Column(String(100), nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # Null for OAuth-only users
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Session tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # OAuth fields
    oauth_provider = Column(String(50), nullable=True)  # google, github, etc.
    oauth_id = Column(String(255), nullable=True)

    # Explicit tenant foreign key (inherited tenant_id from TenantMixin needs FK)
    tenant = relationship(
        "Tenant", back_populates="users", foreign_keys="User.tenant_id"
    )

    # Projects relationship
    projects = relationship("Project", back_populates="owner")
    project_memberships = relationship(
        "ProjectMember", foreign_keys="ProjectMember.user_id", back_populates="user"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
        UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),
    )

    class Config:
        """Pydantic config."""

        from_attributes = True
