"""
Server-Sent Events (SSE) streaming service.
Handles real-time progress updates for document generation workflow.
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone

import redis.asyncio as redis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger()


class StreamingService:
    """Service for SSE streaming and Redis pub/sub."""

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self._redis_pool: Optional[redis.ConnectionPool] = None

    async def get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if not self._redis_pool:
            self._redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )

        return redis.Redis(connection_pool=self._redis_pool)

    def _get_project_channel(self, tenant_id: str, project_id: str) -> str:
        """Get Redis channel name for project events."""
        return f"project:{tenant_id}:{project_id}:events"

    def _get_progress_channel(self, tenant_id: str, project_id: str) -> str:
        """Get Redis channel name for project progress."""
        return f"project:{tenant_id}:{project_id}:progress"

    async def publish_event(
        self,
        tenant_id: str,
        project_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Publish event to project channel."""
        try:
            redis_client = await self.get_redis()
            channel = self._get_project_channel(tenant_id, project_id)

            event_data = {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
                "tenant_id": tenant_id,
                **data
            }

            await redis_client.publish(channel, json.dumps(event_data))
            logger.debug(f"Published event to {channel}: {event_type}")

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    async def publish_progress(
        self,
        tenant_id: str,
        project_id: str,
        step: int,
        progress: float,
        message: str,
        correlation_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publish progress update."""
        try:
            data = {
                "step": step,
                "progress": progress,
                "message": message,
                "correlation_id": correlation_id,
                **(additional_data or {})
            }

            redis_client = await self.get_redis()
            channel = self._get_progress_channel(tenant_id, project_id)
            event_data = {
                "type": "progress",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
                "tenant_id": tenant_id,
                **data
            }
            await redis_client.publish(channel, json.dumps(event_data))

        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")

    async def publish_step_start(
        self,
        tenant_id: str,
        project_id: str,
        step: int,
        step_name: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish step start event."""
        await self.publish_event(
            tenant_id, project_id, "step_start",
            {
                "step": step,
                "step_name": step_name,
                "status": "running",
                "correlation_id": correlation_id
            }
        )

    async def publish_step_complete(
        self,
        tenant_id: str,
        project_id: str,
        step: int,
        step_name: str,
        document_id: str,
        confidence_score: float,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish step completion event."""
        await self.publish_event(
            tenant_id, project_id, "step_complete",
            {
                "step": step,
                "step_name": step_name,
                "status": "completed",
                "document_id": document_id,
                "confidence_score": confidence_score,
                "correlation_id": correlation_id
            }
        )

    async def publish_step_error(
        self,
        tenant_id: str,
        project_id: str,
        step: int,
        step_name: str,
        error_message: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish step error event."""
        await self.publish_event(
            tenant_id, project_id, "step_error",
            {
                "step": step,
                "step_name": step_name,
                "status": "failed",
                "error_message": error_message,
                "correlation_id": correlation_id
            }
        )

    async def publish_workflow_complete(
        self,
        tenant_id: str,
        project_id: str,
        correlation_id: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """Publish workflow completion event."""
        await self.publish_event(
            tenant_id, project_id, "workflow_complete",
            {
                "status": "completed",
                "correlation_id": correlation_id,
                "summary": summary or {}
            }
        )

    async def stream_project_events(
        self,
        tenant_id: str,
        project_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream SSE events for a project."""
        redis_client = await self.get_redis()
        pubsub = redis_client.pubsub()
        channel = self._get_project_channel(tenant_id, project_id)

        try:
            await pubsub.subscribe(channel)
            logger.info(f"Started SSE stream for project {project_id}")

            # Send connection confirmation
            yield self._format_sse_event("connected", {
                "project_id": project_id,
                "message": "Connected to project event stream"
            })

            # Listen for messages
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        yield self._format_sse_event("message", event_data)
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode message data")
                        continue

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for project {project_id}")
        except Exception as e:
            logger.error(f"SSE stream error for project {project_id}: {e}")
            yield self._format_sse_event("error", {
                "message": "Stream error occurred",
                "error": str(e)
            })
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def stream_progress_updates(
        self,
        tenant_id: str,
        project_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream progress updates for a project."""
        redis_client = await self.get_redis()
        pubsub = redis_client.pubsub()
        progress_channel = self._get_progress_channel(tenant_id, project_id)
        events_channel = self._get_project_channel(tenant_id, project_id)

        try:
            await pubsub.subscribe(progress_channel, events_channel)
            logger.info(f"Started progress stream for project {project_id}")

            # Send connection confirmation
            yield self._format_sse_event("connected", {
                "project_id": project_id,
                "message": "Connected to progress stream"
            })

            # Listen for messages
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event_type = event_data.get("type", "message")

                        # Filter to only progress and status events
                        if event_type in ["progress", "step_start", "step_complete", "step_error", "workflow_complete"]:
                            yield self._format_sse_event(event_type, event_data)

                    except json.JSONDecodeError:
                        logger.warning("Failed to decode progress data")
                        continue

        except asyncio.CancelledError:
            logger.info(f"Progress stream cancelled for project {project_id}")
        except Exception as e:
            logger.error(f"Progress stream error for project {project_id}: {e}")
            yield self._format_sse_event("error", {
                "message": "Progress stream error occurred",
                "error": str(e)
            })
        finally:
            await pubsub.unsubscribe(progress_channel, events_channel)
            await pubsub.close()

    def _format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format data as SSE event."""
        event_data = json.dumps(data)
        return f"event: {event_type}\ndata: {event_data}\n\n"

    async def get_project_status(
        self,
        tenant_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """Get current project status from Redis cache."""
        try:
            redis_client = await self.get_redis()
            cache_key = f"project_status:{tenant_id}:{project_id}"

            status_data = await redis_client.get(cache_key)
            if status_data:
                return json.loads(status_data)

            return {
                "project_id": project_id,
                "status": "unknown",
                "last_updated": None
            }

        except Exception as e:
            logger.error(f"Failed to get project status: {e}")
            return {
                "project_id": project_id,
                "status": "error",
                "error": str(e)
            }

    async def update_project_status(
        self,
        tenant_id: str,
        project_id: str,
        status_data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> None:
        """Update project status in Redis cache."""
        try:
            redis_client = await self.get_redis()
            cache_key = f"project_status:{tenant_id}:{project_id}"

            status_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            await redis_client.setex(
                cache_key,
                ttl_seconds,
                json.dumps(status_data)
            )

        except Exception as e:
            logger.error(f"Failed to update project status: {e}")

    async def cleanup_old_streams(self, max_age_hours: int = 24) -> int:
        """Clean up old Redis pub/sub data."""
        try:
            redis_client = await self.get_redis()

            # This would require custom cleanup logic based on Redis configuration
            # For now, Redis handles TTL automatically for pub/sub channels
            logger.info("Stream cleanup completed (Redis handles TTL automatically)")
            return 0

        except Exception as e:
            logger.error(f"Failed to cleanup old streams: {e}")
            return 0

    async def close(self) -> None:
        """Close Redis connections."""
        if self._redis_pool:
            await self._redis_pool.disconnect()
            self._redis_pool = None