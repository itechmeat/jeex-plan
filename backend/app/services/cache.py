"""
Redis caching service for vector database performance optimization.

Provides intelligent caching for search results, embeddings, and frequently
accessed data with automatic tenant isolation and cache management.
"""

import asyncio
import hashlib
import json
from enum import Enum
from typing import Any

from redis.exceptions import RedisError

from app.adapters.redis import RedisAdapter
from app.core.config import settings
from app.core.logger import LoggerMixin, get_logger

logger = get_logger(__name__)


def _cache_json_default(value: Any) -> Any:
    """Provide deterministic serialization for cache key components."""
    if isinstance(value, Enum):
        return value.value

    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except (AttributeError, TypeError, ValueError):
            logger.debug(
                "Failed to serialize value using model_dump", value_type=type(value)
            )

    # Handle collections deterministically
    if isinstance(value, (set, frozenset)):
        # Convert to sorted list with recursive processing
        return sorted([_cache_json_default(item) for item in value])

    if isinstance(value, dict):
        # Sort by keys and recursively process values
        return {k: _cache_json_default(v) for k, v in sorted(value.items())}

    if isinstance(value, (list, tuple)):
        # Process each element recursively, preserving order
        return [_cache_json_default(item) for item in value]

    # For types that cannot be deterministically serialized, raise TypeError
    if hasattr(value, '__dict__') or callable(value):
        typename = type(value).__name__
        raise TypeError(f"Cannot deterministically serialize type {typename}")

    return str(value)


class CacheKey:
    """Utility class for generating consistent cache keys"""

    @staticmethod
    def generate_search_key(
        tenant_id: str,
        project_id: str,
        query_hash: str,
        filters: dict[str, Any],
        limit: int,
    ) -> str:
        """Generate cache key for search results"""
        key_data = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "query_hash": query_hash,
            "filters": sorted(filters.items()),
            "limit": limit,
        }
        return "search:" + hashlib.md5(
            json.dumps(key_data, sort_keys=True, default=_cache_json_default).encode()
        ).hexdigest()

    @staticmethod
    def generate_embedding_key(text: str, model: str, normalization: str) -> str:
        """Generate cache key for text embeddings"""
        key_data = {
            "text_hash": hashlib.md5(text.encode()).hexdigest(),
            "model": model,
            "normalization": normalization,
        }
        json_str = json.dumps(key_data, sort_keys=True).encode()
        return f"embedding:{hashlib.md5(json_str).hexdigest()}"

    @staticmethod
    def generate_stats_key(tenant_id: str, project_id: str) -> str:
        """Generate cache key for collection statistics"""
        return f"stats:{tenant_id}:{project_id}"

    @staticmethod
    def generate_tenant_key(tenant_id: str, key_type: str) -> str:
        """Generate tenant-specific cache key"""
        return f"tenant:{tenant_id}:{key_type}"

    @staticmethod
    def generate_project_index_key(tenant_id: str, project_id: str) -> str:
        """Generate per-project index key for cache invalidation"""
        return f"tenant:{tenant_id}:project:{project_id}:index"


class VectorCache(LoggerMixin):
    """
    High-performance caching service for vector operations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.redis = RedisAdapter()
        self.default_ttl = settings.CACHE_DEFAULT_TTL
        self.search_ttl = settings.CACHE_SEARCH_TTL
        self.embedding_ttl = settings.CACHE_EMBEDDING_TTL
        self.stats_ttl = settings.CACHE_STATS_TTL

        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0

    async def get_search_results(
        self,
        tenant_id: str,
        project_id: str,
        query_hash: str,
        filters: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]] | None:
        """
        Get cached search results if available.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query_hash: Hash of the query vector
            filters: Search filters used
            limit: Result limit

        Returns:
            Cached search results or None
        """
        try:
            cache_key = CacheKey.generate_search_key(
                tenant_id, project_id, query_hash, filters, limit
            )

            cached_data = await self.redis.get(cache_key)
            if cached_data:
                results = json.loads(cached_data)
                self.cache_hits += 1

                logger.debug(
                    "Search cache hit",
                    tenant_id=tenant_id,
                    project_id=project_id,
                    cache_key=cache_key[:16] + "...",
                )

                return results

            self.cache_misses += 1
            return None

        except (RedisError, json.JSONDecodeError) as exc:
            logger.warning("Search cache retrieval failed", error=str(exc))
            self.cache_misses += 1
            return None

    async def set_search_results(
        self,
        tenant_id: str,
        project_id: str,
        query_hash: str,
        filters: dict[str, Any],
        limit: int,
        results: list[dict[str, Any]],
    ) -> bool:
        """
        Cache search results with automatic TTL.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query_hash: Hash of the query vector
            filters: Search filters used
            limit: Result limit
            results: Search results to cache

        Returns:
            True if cached successfully
        """
        try:
            cache_key = CacheKey.generate_search_key(
                tenant_id, project_id, query_hash, filters, limit
            )

            # Store with tenant-specific prefix for easy invalidation
            success = await self.redis.set(
                cache_key, json.dumps(results), ex=self.search_ttl
            )

            if success:
                # Add to tenant and project cache indices for invalidation
                await self._add_to_tenant_index(tenant_id, cache_key)
                await self._add_to_project_index(tenant_id, project_id, cache_key)

                logger.debug(
                    "Search results cached",
                    tenant_id=tenant_id,
                    project_id=project_id,
                    results_count=len(results),
                    ttl=self.search_ttl,
                )

            return success

        except (RedisError, TypeError) as exc:
            logger.warning("Search cache storage failed", error=str(exc))
            return False

    async def get_embedding(
        self, text: str, model: str, normalization: str
    ) -> list[float] | None:
        """
        Get cached embedding if available.

        Args:
            text: Input text
            model: Embedding model used
            normalization: Normalization applied

        Returns:
            Cached embedding vector or None
        """
        try:
            cache_key = CacheKey.generate_embedding_key(text, model, normalization)

            cached_data = await self.redis.get(cache_key)
            if cached_data:
                embedding = json.loads(cached_data)
                self.cache_hits += 1

                logger.debug(
                    "Embedding cache hit",
                    model=model,
                    normalization=normalization,
                    text_length=len(text),
                )

                return embedding

            self.cache_misses += 1
            return None

        except (RedisError, json.JSONDecodeError) as exc:
            logger.warning("Embedding cache retrieval failed", error=str(exc))
            self.cache_misses += 1
            return None

    async def set_embedding(
        self, text: str, model: str, normalization: str, embedding: list[float]
    ) -> bool:
        """
        Cache embedding with automatic TTL.

        Args:
            text: Input text
            model: Embedding model used
            normalization: Normalization applied
            embedding: Embedding vector to cache

        Returns:
            True if cached successfully
        """
        try:
            cache_key = CacheKey.generate_embedding_key(text, model, normalization)

            success = await self.redis.set(
                cache_key, json.dumps(embedding), ex=self.embedding_ttl
            )

            if success:
                logger.debug(
                    "Embedding cached",
                    model=model,
                    normalization=normalization,
                    text_length=len(text),
                    vector_dim=len(embedding),
                )

            return success

        except (RedisError, TypeError) as exc:
            logger.warning("Embedding cache storage failed", error=str(exc))
            return False

    async def get_collection_stats(
        self, tenant_id: str, project_id: str
    ) -> dict[str, Any] | None:
        """
        Get cached collection statistics.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier

        Returns:
            Cached statistics or None
        """
        try:
            cache_key = CacheKey.generate_stats_key(tenant_id, project_id)

            cached_data = await self.redis.get(cache_key)
            if cached_data:
                stats = json.loads(cached_data)
                self.cache_hits += 1

                logger.debug(
                    "Stats cache hit", tenant_id=tenant_id, project_id=project_id
                )

                return stats

            self.cache_misses += 1
            return None

        except (RedisError, json.JSONDecodeError) as exc:
            logger.warning("Stats cache retrieval failed", error=str(exc))
            self.cache_misses += 1
            return None

    async def set_collection_stats(
        self, tenant_id: str, project_id: str, stats: dict[str, Any]
    ) -> bool:
        """
        Cache collection statistics.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            stats: Statistics to cache

        Returns:
            True if cached successfully
        """
        try:
            cache_key = CacheKey.generate_stats_key(tenant_id, project_id)

            # Shorter TTL for stats as they change more frequently
            success = await self.redis.set(
                cache_key, json.dumps(stats), ex=self.stats_ttl
            )

            if success:
                # Add to project index for invalidation
                await self._add_to_project_index(tenant_id, project_id, cache_key)

                logger.debug("Stats cached", tenant_id=tenant_id, project_id=project_id)

            return success

        except (RedisError, TypeError) as exc:
            logger.warning("Stats cache storage failed", error=str(exc))
            return False

    async def invalidate_tenant_cache(self, tenant_id: str) -> int:
        """
        Invalidate all cache entries for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Number of cache keys invalidated
        """
        try:
            index_key = CacheKey.generate_tenant_key(tenant_id, "index")
            cache_keys = await self.redis.smembers(index_key)

            if not cache_keys:
                return 0

            # Delete all cached keys
            deleted_count = 0
            for cache_key in cache_keys:
                if await self.redis.delete(cache_key):
                    deleted_count += 1

            # Delete the index
            await self.redis.delete(index_key)

            logger.info(
                "Tenant cache invalidated",
                tenant_id=tenant_id,
                keys_deleted=deleted_count,
            )

            return deleted_count

        except RedisError as exc:
            logger.error("Tenant cache invalidation failed", error=str(exc))
            return 0

    async def invalidate_project_cache(self, tenant_id: str, project_id: str) -> int:
        """
        Invalidate cache entries for a specific project.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier

        Returns:
            Number of cache keys invalidated
        """
        try:
            # Use indexed membership instead of KEYS scan
            index_key = CacheKey.generate_project_index_key(tenant_id, project_id)
            cache_keys = await self.redis.smembers(index_key)
            if not cache_keys:
                return 0

            deleted_count = 0
            for cache_key in cache_keys:
                if await self.redis.delete(cache_key):
                    deleted_count += 1

            # Clear the project index
            await self.redis.delete(index_key)

            self.logger.info(
                "Project cache invalidated",
                tenant_id=tenant_id,
                project_id=project_id,
                keys_deleted=deleted_count,
            )

            return deleted_count

        except RedisError as exc:
            self.logger.exception(
                "Project cache invalidation failed", error=str(exc)
            )
            return 0

    async def _add_to_tenant_index(self, tenant_id: str, cache_key: str) -> bool:
        """Add cache key to tenant index for invalidation"""
        try:
            index_key = CacheKey.generate_tenant_key(tenant_id, "index")
            return await self.redis.sadd(index_key, cache_key)
        except RedisError as exc:
            logger.warning("Failed to add to tenant index", error=str(exc))
            return False

    async def _add_to_project_index(
        self, tenant_id: str, project_id: str, cache_key: str
    ) -> bool:
        """Add cache key to project index for invalidation"""
        try:
            index_key = CacheKey.generate_project_index_key(tenant_id, project_id)
            return await self.redis.sadd(index_key, cache_key)
        except RedisError as exc:
            logger.warning("Failed to add to project index", error=str(exc))
            return False

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "default_ttl": self.default_ttl,
            "search_ttl": self.search_ttl,
            "embedding_ttl": self.embedding_ttl,
        }

    async def warm_up_cache(
        self, tenant_id: str, project_id: str, common_queries: list[str]
    ) -> dict[str, Any]:
        """
        Pre-warm cache with common queries for a project.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            common_queries: List of common search queries

        Returns:
            Warm-up statistics
        """
        try:
            from app.services.embedding import EmbeddingService

            embedding_service = EmbeddingService()

            warmed_count = 0
            failed_count = 0

            warmup_exceptions = (
                RuntimeError,
                ValueError,
                KeyError,
                TypeError,
                RedisError,
            )

            for query in common_queries:
                try:
                    embedding_result = await embedding_service.process_document(
                        text=query,
                        metadata={"purpose": "cache_warmup"},
                    )

                    if embedding_result.embeddings:
                        await self.set_embedding(
                            text=query,
                            model=embedding_result.model_used,
                            normalization="standard",
                            embedding=embedding_result.embeddings[0],
                        )
                        warmed_count += 1

                    await asyncio.sleep(settings.CACHE_WARMUP_DELAY_SEC)

                except warmup_exceptions as exc:
                    logger.warning(
                        "Cache warm-up failed for query",
                        query=query[:50],
                        error=str(exc),
                    )
                    failed_count += 1

            logger.info(
                "Cache warm-up completed",
                tenant_id=tenant_id,
                project_id=project_id,
                warmed_count=warmed_count,
                failed_count=failed_count,
            )

            return {
                "warmed_count": warmed_count,
                "failed_count": failed_count,
                "total_queries": len(common_queries),
            }

        except (RedisError, RuntimeError, ValueError, TypeError) as exc:
            logger.error("Cache warm-up failed", error=str(exc))
            return {
                "warmed_count": 0,
                "failed_count": len(common_queries),
                "error": str(exc),
            }


# Singleton instance for application-wide use
vector_cache = VectorCache()
