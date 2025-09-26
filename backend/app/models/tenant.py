"""
Tenant model for multi-tenancy support.
"""

import uuid

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    """Tenant entity for multi-tenant architecture."""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Configuration
    max_projects = Column(Integer, nullable=True)  # None = unlimited
    max_storage_mb = Column(Integer, nullable=True)  # None = unlimited

    # Relationships
    users = relationship("User", back_populates="tenant")
    projects = relationship("Project", back_populates="tenant")
