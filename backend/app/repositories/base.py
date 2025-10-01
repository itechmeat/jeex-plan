"""
Base repository classes for data access patterns.
"""

from abc import ABC
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import get_logger
from app.models.base import BaseModel

logger = get_logger()
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(ABC, Generic[ModelType]):
    """Base repository with common async CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new entity."""
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            await (
                self.session.flush()
            )  # Use flush instead of commit for better transaction control

            # SECURITY: NO fallback to "unknown" - entity ID MUST be determinable
            try:
                await self.session.refresh(instance)
                # Verify ID was assigned after refresh
                if not hasattr(instance, "id") or instance.id is None:
                    raise ValueError(
                        f"Entity ID not assigned after refresh for {self.model.__name__}"
                    )
                entity_id = str(instance.id)
            except Exception as refresh_exc:
                # Refresh failed - try to get ID directly from instance
                _id = getattr(instance, "id", None)
                if _id is None:
                    # CRITICAL: Entity ID cannot be determined - raise explicit error
                    logger.error(
                        "Entity ID not assigned after flush/refresh",
                        model=self.model.__name__,
                        refresh_error=str(refresh_exc),
                    )
                    raise ValueError(
                        f"Failed to determine entity ID for {self.model.__name__}. "
                        f"Database may not support RETURNING clause or ID generation failed."
                    ) from refresh_exc
                entity_id = str(_id)

            logger.info(
                "Created entity",
                model=self.model.__name__,
                entity_id=entity_id,
            )
            return instance
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error(
                "Failed to create entity",
                model=self.model.__name__,
                error=str(exc),
            )
            raise exc
        except ValueError:
            await self.session.rollback()
            raise  # Re-raise ID assignment errors

    async def get_by_id(self, entity_id: UUID) -> ModelType | None:
        """Get entity by ID."""
        stmt = select(self.model).where(
            and_(self.model.id == entity_id, self.model.is_deleted.is_(False))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        """Get all entities with optional filtering."""
        stmt = select(self.model).where(self.model.is_deleted.is_(False))

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    column_attr = getattr(self.model, field)
                    if isinstance(value, bool):
                        stmt = stmt.where(column_attr.is_(value))
                    else:
                        stmt = stmt.where(column_attr == value)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_eager(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        eager_loads: list[str] | None = None,
    ) -> list[ModelType]:
        """Get all entities with optional filtering and eager loading."""
        stmt = select(self.model).where(self.model.is_deleted.is_(False))

        # Apply eager loading
        if eager_loads:
            for load_path in eager_loads:
                if hasattr(self.model, load_path):
                    stmt = stmt.options(selectinload(getattr(self.model, load_path)))

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    column_attr = getattr(self.model, field)
                    if isinstance(value, bool):
                        stmt = stmt.where(column_attr.is_(value))
                    else:
                        stmt = stmt.where(column_attr == value)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, entity_id: UUID, **kwargs: Any) -> ModelType | None:
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
            update_data["updated_at"] = datetime.now(UTC)

            ignored_fields = []
            for field, value in update_data.items():
                if field in protected_fields:
                    ignored_fields.append(field)
                    continue
                if hasattr(instance, field):
                    setattr(instance, field, value)

            if ignored_fields:
                logger.warning(
                    "Ignored protected fields during update",
                    fields=ignored_fields,
                    model=self.model.__name__,
                )

            await (
                self.session.flush()
            )  # Use flush instead of commit for better transaction control
            await self.session.refresh(instance)
            logger.info(
                "Updated entity",
                model=self.model.__name__,
                entity_id=str(entity_id),
            )
            return instance
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error(
                "Failed to update entity",
                model=self.model.__name__,
                entity_id=str(entity_id),
                error=str(exc),
            )
            raise exc

    async def delete(self, entity_id: UUID, *, soft_delete: bool = True) -> bool:
        """Delete entity (soft or hard delete)."""
        try:
            instance = await self.get_by_id(entity_id)
            if not instance:
                return False

            if soft_delete:
                instance.is_deleted = True
                instance.deleted_at = datetime.now(UTC)
                await self.session.flush()
                logger.info(
                    "Soft deleted entity",
                    model=self.model.__name__,
                    entity_id=str(entity_id),
                )
            else:
                await self.session.delete(instance)
                await self.session.flush()
                logger.info(
                    "Hard deleted entity",
                    model=self.model.__name__,
                    entity_id=str(entity_id),
                )

            return True
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error(
                "Failed to delete entity",
                model=self.model.__name__,
                entity_id=str(entity_id),
                error=str(exc),
            )
            raise exc

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities with optional filtering."""
        stmt = select(func.count(self.model.id)).where(self.model.is_deleted.is_(False))

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    column_attr = getattr(self.model, field)
                    if isinstance(value, bool):
                        stmt = stmt.where(column_attr.is_(value))
                    else:
                        stmt = stmt.where(column_attr == value)

        result = await self.session.execute(stmt)
        count_value = result.scalar()
        return int(count_value or 0)

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists."""
        stmt = select(self.model.id).where(
            and_(self.model.id == entity_id, self.model.is_deleted.is_(False))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


class TenantRepository(BaseRepository[ModelType]):
    """Repository with tenant isolation."""

    def __init__(
        self, session: AsyncSession, model: type[ModelType], tenant_id: UUID
    ) -> None:
        super().__init__(session, model)
        self.tenant_id = tenant_id

    async def create(self, **kwargs: Any) -> ModelType:
        """Create entity with tenant isolation."""
        kwargs["tenant_id"] = self.tenant_id
        return await super().create(**kwargs)

    async def get_by_id(self, entity_id: UUID) -> ModelType | None:
        """Get entity by ID within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.id == entity_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        """Get all entities within tenant."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id, self.model.is_deleted.is_(False)
            )
        )

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    column_attr = getattr(self.model, field)
                    if isinstance(value, bool):
                        stmt = stmt.where(column_attr.is_(value))
                    else:
                        stmt = stmt.where(column_attr == value)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_eager(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        eager_loads: list[str] | None = None,
    ) -> list[ModelType]:
        """Get all entities within tenant with eager loading."""
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id, self.model.is_deleted.is_(False)
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
                    column_attr = getattr(self.model, field)
                    if isinstance(value, bool):
                        stmt = stmt.where(column_attr.is_(value))
                    else:
                        stmt = stmt.where(column_attr == value)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities within tenant."""
        stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.tenant_id == self.tenant_id, self.model.is_deleted.is_(False)
            )
        )

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    column_attr = getattr(self.model, field)
                    if isinstance(value, bool):
                        stmt = stmt.where(column_attr.is_(value))
                    else:
                        stmt = stmt.where(column_attr == value)

        result = await self.session.execute(stmt)
        count_value = result.scalar()
        return int(count_value or 0)

    async def get_by_field(
        self, field_name: str, field_value: object
    ) -> ModelType | None:
        """Get entity by field within tenant with SQL injection protection."""
        if not hasattr(self.model, field_name):
            logger.warning(
                "Field not found in model",
                field_name=field_name,
                model=self.model.__name__,
            )
            return None

        # Validate field name to prevent SQL injection
        if not field_name.isidentifier():
            logger.error("Invalid field name", field_name=field_name)
            raise ValueError(f"Invalid field name: {field_name}")

        column_attr = getattr(self.model, field_name)

        # Use parameterized queries to prevent SQL injection
        if isinstance(field_value, bool):
            comparison = column_attr.is_(field_value)
        elif field_value is None:
            comparison = column_attr.is_(None)
        else:
            comparison = column_attr == field_value

        stmt = select(self.model).where(
            and_(
                comparison,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
            )
        )

        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            logger.error("Database error in get_by_field", error=str(exc))
            raise exc

    async def get_by_fields(self, **filters: object) -> list[ModelType]:
        """Get entities matching multiple fields within tenant."""
        conditions = [
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
        ]

        for field, value in filters.items():
            if not hasattr(self.model, field):
                continue
            column_attr = getattr(self.model, field)
            if isinstance(value, bool):
                conditions.append(column_attr.is_(value))
            else:
                conditions.append(column_attr == value)

        stmt = select(self.model).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        search_fields: list[str],
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Search entities within tenant with SQL injection protection."""
        if not search_fields or not search_term:
            return []

        # Validate search fields to prevent SQL injection
        validated_fields = []
        for field in search_fields:
            if not field.isidentifier():
                logger.warning("Invalid search field name", field_name=field)
                continue
            if not hasattr(self.model, field):
                logger.warning(
                    "Field not found in model",
                    field_name=field,
                    model=self.model.__name__,
                )
                continue
            validated_fields.append(field)

        if not validated_fields:
            return []

        # Sanitize search term to prevent SQL injection
        if len(search_term.strip()) == 0:
            return []

        # Limit search term length to prevent DoS attacks
        if len(search_term) > 200:
            search_term = search_term[:200]

        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == self.tenant_id, self.model.is_deleted.is_(False)
            )
        )

        # Add search conditions using parameterized queries
        search_conditions = []
        for field_name in validated_fields:
            field_attr = getattr(self.model, field_name)
            # Use parameter binding to prevent SQL injection
            search_conditions.append(field_attr.ilike(f"%{search_term}%"))

        if search_conditions:
            stmt = stmt.where(or_(*search_conditions))

        # Validate and apply pagination limits
        skip = max(0, skip)
        limit = max(1, min(limit, 1000))  # Cap at 1000 to prevent memory issues

        stmt = stmt.offset(skip).limit(limit)

        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            logger.error("Database error in search", error=str(exc))
            raise exc

    async def bulk_update(
        self, filters: dict[str, Any], updates: dict[str, Any]
    ) -> int:
        """Bulk update entities within tenant."""
        try:
            # Add tenant filter and soft delete filter
            filters["tenant_id"] = self.tenant_id
            filters["is_deleted"] = False

            # Add updated timestamp and protect tenant field
            updates = dict(updates)
            updates["updated_at"] = datetime.now(UTC)
            updates.pop("tenant_id", None)

            conditions = []
            for key, value in filters.items():
                column_attr = getattr(self.model, key)
                if isinstance(value, bool):
                    conditions.append(column_attr.is_(value))
                else:
                    conditions.append(column_attr == value)

            stmt = update(self.model).where(and_(*conditions)).values(**updates)

            result = await self.session.execute(
                stmt.execution_options(synchronize_session=False)
            )
            await self.session.flush()

            logger.info(
                "Bulk updated records",
                model=self.model.__name__,
                updated_count=result.rowcount,
            )
            return result.rowcount
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error(
                "Failed to bulk update",
                model=self.model.__name__,
                error=str(exc),
            )
            raise exc

    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists within tenant."""
        stmt = select(self.model.id).where(
            and_(
                self.model.id == entity_id,
                self.model.tenant_id == self.tenant_id,
                self.model.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
