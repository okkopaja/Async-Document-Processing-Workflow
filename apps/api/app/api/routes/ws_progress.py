"""WebSocket routes for real-time job and document progress."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis as AsyncRedis

from app.core.config import settings
from app.integrations.redis_pubsub import subscribe_to_channel

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy-initialized async Redis client for API context
_redis_client: AsyncRedis[Any] | None = None


async def _get_redis_client() -> AsyncRedis[Any]:
	"""Get or initialize the async Redis client for API context."""
	global _redis_client
	if _redis_client is None:
		try:
			_redis_client = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
			await _redis_client.ping()
			logger.info("Async Redis client initialized for API context")
		except Exception as exc:
			logger.error(f"Failed to initialize Redis client: {exc}")
			raise
	return _redis_client


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str) -> None:
	"""
	WebSocket endpoint for subscribing to job progress events.

	Messages are relayed from Redis Pub/Sub channel: job:{job_id}:progress

	Args:
	    websocket: WebSocket connection
	    job_id: UUID string of the processing job
	"""
	await websocket.accept()
	logger.info(f"WebSocket client connected to job:{job_id}:progress")

	try:
		redis_client = await _get_redis_client()
		channel = f"job:{job_id}:progress"

		# Subscribe to Redis Pub/Sub channel and relay to WebSocket
		async for event in subscribe_to_channel(redis_client, channel):
			try:
				await websocket.send_json(event)
				logger.debug(
					"Progress event sent to WebSocket client",
					extra={
						"job_id": job_id,
						"stage": event.get("stage"),
						"progress": event.get("progressPercent"),
					},
				)
			except Exception as exc:
				logger.warning(f"Failed to send event to WebSocket: {exc}")
				break

	except WebSocketDisconnect:
		logger.info(f"WebSocket client disconnected from job:{job_id}:progress")

	except Exception as exc:
		logger.exception(
			"Error in WebSocket job progress handler",
			extra={"job_id": job_id, "error": str(exc)},
		)
		try:
			await websocket.close(code=1011, reason="Internal server error")
		except Exception:
			pass

	finally:
		logger.debug(f"WebSocket job progress handler cleaned up for job:{job_id}")


@router.websocket("/ws/documents/{document_id}")
async def websocket_document_progress(websocket: WebSocket, document_id: str) -> None:
	"""
	WebSocket endpoint for subscribing to document progress events.

	Messages are relayed from Redis Pub/Sub channel: document:{document_id}:progress

	Args:
	    websocket: WebSocket connection
	    document_id: UUID string of the document
	"""
	await websocket.accept()
	logger.info(f"WebSocket client connected to document:{document_id}:progress")

	try:
		redis_client = await _get_redis_client()
		channel = f"document:{document_id}:progress"

		# Subscribe to Redis Pub/Sub channel and relay to WebSocket
		async for event in subscribe_to_channel(redis_client, channel):
			try:
				await websocket.send_json(event)
				logger.debug(
					"Progress event sent to WebSocket client",
					extra={
						"document_id": document_id,
						"stage": event.get("stage"),
						"progress": event.get("progressPercent"),
					},
				)
			except Exception as exc:
				logger.warning(f"Failed to send event to WebSocket: {exc}")
				break

	except WebSocketDisconnect:
		logger.info(f"WebSocket client disconnected from document:{document_id}:progress")

	except Exception as exc:
		logger.exception(
			"Error in WebSocket document progress handler",
			extra={"document_id": document_id, "error": str(exc)},
		)
		try:
			await websocket.close(code=1011, reason="Internal server error")
		except Exception:
			pass

	finally:
		logger.debug(f"WebSocket document progress handler cleaned up for document:{document_id}")
