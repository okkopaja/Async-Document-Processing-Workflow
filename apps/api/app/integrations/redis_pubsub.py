"""Redis Pub/Sub integration for real-time progress events."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis
from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)


class ProgressPublisher:
    """Publishes document processing progress events to Redis Pub/Sub."""

    def __init__(self, redis_client: redis.Redis[Any] | None = None):
        """
        Initialize publisher with Redis client.

        Args:
            redis_client: Synchronous Redis client for worker context.
                         If None, will be initialized on first use.
        """
        self.redis = redis_client

    async def publish_progress_async(
        self,
        job_id: str,
        document_id: str,
        status: str,
        stage: str,
        progress_percent: int,
        message: str,
        attempt_number: int = 1,
        redis_client: AsyncRedis[Any] | None = None,
    ) -> None:
        """
        Publish progress event to Redis Pub/Sub (async version for API context).

        Args:
            job_id: Processing job ID
            document_id: Document ID
            status: Job status (QUEUED, PROCESSING, COMPLETED, FAILED)
            stage: Current pipeline stage
            progress_percent: Progress percentage (0-100)
            message: Human-readable progress message
            attempt_number: Job attempt number (for retries)
            redis_client: Async Redis client (required for async context)
        """
        if not redis_client:
            logger.warning("Async Redis client not provided; skipping publish")
            return

        try:
            event = {
                "eventId": str(uuid4()),
                "jobId": job_id,
                "documentId": document_id,
                "status": status,
                "stage": stage,
                "progressPercent": progress_percent,
                "message": message,
                "attemptNumber": attempt_number,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            channels = [
                f"job:{job_id}:progress",
                f"document:{document_id}:progress",
            ]

            for channel in channels:
                await redis_client.publish(channel, json.dumps(event))

            logger.debug(
                "Progress event published",
                extra={
                    "job_id": job_id,
                    "stage": stage,
                    "channels": channels,
                },
            )

        except Exception:
            logger.exception("Error publishing progress event", extra={"job_id": job_id})
            # Don't fail the task; just log the error

    def publish_progress(
        self,
        job_id: str,
        document_id: str,
        status: str,
        stage: str,
        progress_percent: int,
        message: str,
        attempt_number: int = 1,
    ) -> None:
        """
        Publish progress event to Redis Pub/Sub (sync version for worker context).

        Args:
            job_id: Processing job ID
            document_id: Document ID
            status: Job status (QUEUED, PROCESSING, COMPLETED, FAILED)
            stage: Current pipeline stage
            progress_percent: Progress percentage (0-100)
            message: Human-readable progress message
            attempt_number: Job attempt number (for retries)
        """
        if not self.redis:
            logger.warning("Redis client not initialized; skipping publish")
            return

        try:
            event = {
                "eventId": str(uuid4()),
                "jobId": job_id,
                "documentId": document_id,
                "status": status,
                "stage": stage,
                "progressPercent": progress_percent,
                "message": message,
                "attemptNumber": attempt_number,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            channels = [
                f"job:{job_id}:progress",
                f"document:{document_id}:progress",
            ]

            for channel in channels:
                self.redis.publish(channel, json.dumps(event))

            logger.debug(
                "Progress event published",
                extra={
                    "job_id": job_id,
                    "stage": stage,
                    "channels": channels,
                },
            )

        except Exception:
            logger.exception("Error publishing progress event", extra={"job_id": job_id})
            # Don't fail the task; just log the error


async def subscribe_to_channel(
    redis_client: AsyncRedis[Any], channel: str
):
    """
    Subscribe to a Redis Pub/Sub channel and yield messages.

    Args:
        redis_client: Async Redis client
        channel: Channel name to subscribe to

    Yields:
        Parsed JSON event messages from the channel
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    yield data
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in channel {channel}: {message['data']}")
    finally:
        await pubsub.close()


def get_progress_publisher(redis_client: redis.Redis[Any] | None = None) -> ProgressPublisher:
    """Get a configured progress publisher instance."""
    return ProgressPublisher(redis_client=redis_client)
