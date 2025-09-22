"""
Base repository classes for data access patterns.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, func, update, delete
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.models.base import BaseModel
from app.core.logger import get_logger

logger = get_logger()
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType], ABC):
    """Base repository with common async CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def create(self, **kwargs) -> ModelType:
        """Create a new entity."""
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            logger.info(f"Created {self.model.__name__} with id {instance.id}")
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise e

    async def get_by_id(self, entity_id: UUID) -> Optional[ModelType]:
        """Get entity by ID."""
        stmt = select(self.model).where(
            and_(
                self.model.id == entity_id,
                self.model.is_deleted == False
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get all entities with optional filtering."""
        stmt = select(self.model).where(self.model.is_deleted == False)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_eager(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        eager_loads: Optional[List[str]] = None
    ) -> List[ModelType]:
        """Get all entities with optional filtering and eager loading."""
        stmt = select(self.model).where(self.model.is_deleted == False)

        # Apply eager loading
        if eager_loads:
            for load_path in eager_loads:
                if hasattr(self.model, load_path):
                    stmt = stmt.options(selectinload(getattr(self.model, load_path)))

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, entity_id: UUID, **kwargs) -> Optional[ModelType]:
        """Update entity by ID."""
        try:
            instance = await self.get_by_id(entity_id)
            if not instance:
                return None

            protected_fields = {"id", "tenant_id", "created_at"}
            # also protect potential mixin aliases
            if hasattr(instance, "tenant_id"):
                protected_fields.add("tenant_id")

            # Update timestamp
            update_data = dict(kwargs)
            update_data['updated_at'] = datetime.utcnow()

            ignored_fields = []
            for field, value in update_data.items():
                if field in protected_fields:
                    ignored_fields.append(field)
                    continue
                if hasattr(instance, field):
                    setattr(instance, field, value)

            if ignored_fields:
                logger.warning(
                    "Ignored protected fields during update", fields=ignored_fields, model=self.model.__name__
                )

            await self.session.commit()
            await self.session.refresh(instance)
            logger.info(f"Updated {self.model.__name__} with id {entity_id}")
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to update {self.model.__name__} {entity_id}: {e}")
            raise e

    async def delete(self, entity_id: UUID, soft_delete: bool = True) -> bool:
        """Delete entity (soft or hard delete)."""
        try:
            instance = await self.get_by_id(entity_id)
            if not instance:
                return False

            if soft_delete:
                instance.is_deleted = True
                instance.deleted_at = datetime.utcnow()
                await self.session.commit()
                logger.info(f"Soft deleted {self.model.__name__} with id {entity_id}")
            else:
                await self.session.delete(instance)
                await self.session.commit()
                logger.info(f"Hard deleted {self.model.__name__} with id {entity_id}")

            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to delete {self.model.__name__} {entity_id}: {e}")
            raise e

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering."""
        stmt = select(func.count(self.model.id)).where(self.model.is_deleted == False)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.session.execute(stmt)
        return result.scalar()

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists."""
        stmt = select(self.model.id).where(
            and_(
                self.model.id == entity_id,
                self.model.is_deleted == False
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


class TenantRepository(BaseRepository[ModelType]):
    """Repository with tenant isolation."""

    def __init__(self, session: AsyncSession, model: Type[ModelType], tenant_id: UUID):
        super().__init__(session, model)
        self.tenant_id = tenant_id

    async def create(self, **kwargs) -> ModelType:
        """Create entity with tenant isolation."""
        kwargs['tenant_id'] = self.tenant_id
        return await super().create(**kwargs)

    async def get_by_id(self, entity_id: UUID) -> Optional[ModelType]:
        """Get entity by ID within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.id == entity_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get all entities within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_eager(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        eager_loads: Optional[List[str]] = None
    ) -> List[ModelType]:
        """Get all entities within tenant with eager loading."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )

        # Apply eager loading
        if eager_loads:
            for load_path in eager_loads:
                if hasattr(self.model, load_path):
                    stmt = stmt.options(selectinload(getattr(self.model, load_path)))

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities within tenant."""
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.session.execute(stmt)
        return result.scalar()

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[ModelType]:
        """Get entity by field within tenant."""
        if not hasattr(self.model, field_name):
            return None

        stmt = select(self.model).where(
            and_(
                getattr(self.model, field_name) == field_value,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        search_fields: List[str],
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Search entities within tenant."""
        if not search_fields or not search_term:
            return []

        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )

        # Add search conditions
        search_conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                search_conditions.append(field_attr.ilike(f"%{search_term}%"))

        if search_conditions:
            stmt = stmt.where(or_(*search_conditions))

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_update(
        self,
        filters: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> int:
        """Bulk update entities within tenant."""
        try:
            # Add tenant filter and soft delete filter
            filters['tenant_id'] = self.tenant_id
            filters['is_deleted'] = False

            # Add updated timestamp and protect tenant field
            updates = dict(updates)
            updates['updated_at'] = datetime.utcnow()
            updates.pop('tenant_id', None)

            stmt = update(self.model).where(
                and_(*[getattr(self.model, k) == v for k, v in filters.items()])
            ).values(**updates)

            result = await self.session.execute(stmt.execution_options(synchronize_session=False))
            await self.session.commit()

            logger.info(f"Bulk updated {result.rowcount} {self.model.__name__} records")
            return result.rowcount
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to bulk update {self.model.__name__}: {e}")
            raise e

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists within tenant."""
        stmt = select(self.model.id).where(
            and_(
                self.model.id == entity_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted == False
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
