"""Document processing task — main Celery entrypoint."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.constants import (
	DocumentStatus,
	JobStage,
	PermanentParseError,
	TransientParseError,
	UnsupportedFileTypeError,
)
from app.integrations.redis_pubsub import ProgressPublisher
from app.repositories.documents import DocumentsRepository
from app.repositories.jobs import JobsRepository
from app.repositories.events import EventsRepository
from app.workers.pipelines.parse_stage import parse_stage
from app.workers.pipelines.extract_stage import extract_stage
from app.workers.pipelines.persist_stage import persist_stage

logger = logging.getLogger(__name__)

# Create async engine and sessionmaker for Celery worker context
engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Lazy-initialized Redis client for Celery worker context (sync)
_redis_client: redis.Redis[Any] | None = None
_progress_publisher: ProgressPublisher | None = None


def _get_redis_client() -> redis.Redis[Any]:
	"""Get or initialize the synchronous Redis client for worker context."""
	global _redis_client
	if _redis_client is None:
		try:
			_redis_client = redis.from_url(settings.redis_url, decode_responses=True)
			_redis_client.ping()
			logger.info("Redis client initialized for worker context")
		except Exception as exc:
			logger.error(f"Failed to initialize Redis client: {exc}")
			# Return a dummy client that won't crash
			_redis_client = None
	return _redis_client


def _get_progress_publisher() -> ProgressPublisher:
	"""Get or initialize the progress publisher."""
	global _progress_publisher
	if _progress_publisher is None:
		redis_client = _get_redis_client()
		_progress_publisher = ProgressPublisher(redis_client=redis_client)
	return _progress_publisher


async def _get_db_session() -> AsyncSession:
	"""Get async DB session for worker tasks."""
	return SessionLocal()


async def _emit_progress(
	session: AsyncSession,
	job_id: str,
	document_id: str,
	status: str,
	stage: str,
	progress_percent: int,
	message: str,
	attempt_number: int = 1,
) -> None:
	"""
	Emit progress event: update DB, insert event row, and publish to Redis Pub/Sub.

	Execution order (per architectural rules):
	1. Update PostgreSQL state (job status/stage/progress)
	2. Insert job_events row
	3. Publish Redis Pub/Sub event

	Args:
	    session: Async DB session
	    job_id: Processing job ID
	    document_id: Document ID
	    status: Job status (QUEUED, PROCESSING, COMPLETED, FAILED)
	    stage: Current pipeline stage
	    progress_percent: Progress percentage (0-100)
	    message: Human-readable progress message
	    attempt_number: Job attempt number (for retries)
	"""
	try:
		# 1. Update job status in DB
		jobs_repo = JobsRepository()
		updated_job = await jobs_repo.update_status(
			session=session,
			job_id=job_id,
			status=status,
			stage=stage,
			progress=progress_percent,
		)
		if not updated_job:
			logger.warning(
				"Skipping progress emit because job does not exist",
				extra={"job_id": job_id, "stage": stage},
			)
			return

		# 2. Insert job event
		events_repo = EventsRepository()
		await events_repo.create(
			session=session,
			job_id=job_id,
			event_type=stage,
			payload={
				"documentId": document_id,
				"status": status,
				"progress": progress_percent,
				"message": message,
			},
		)

		# Commit changes to PostgreSQL first
		await session.commit()

		logger.debug(
			"Progress state updated in DB",
			extra={
				"job_id": job_id,
				"stage": stage,
				"progress": progress_percent,
			},
		)

		# 3. Publish to Redis Pub/Sub (transient layer for real-time UI updates)
		# This happens AFTER DB commit to ensure state durability
		publisher = _get_progress_publisher()
		publisher.publish_progress(
			job_id=job_id,
			document_id=document_id,
			status=status,
			stage=stage,
			progress_percent=progress_percent,
			message=message,
			attempt_number=attempt_number,
		)

		logger.debug(
			"Progress event published to Redis",
			extra={
				"job_id": job_id,
				"stage": stage,
				"progress": progress_percent,
			},
		)

	except Exception:
		logger.exception("Error emitting progress", extra={"job_id": job_id})
		# Don't fail the task; just log it
		try:
			await session.rollback()
		except Exception:
			pass


async def _process_document_async(job_id: str, document_id: str) -> None:
	"""
	Async implementation of document processing task.

	Stages:
	1. Load document and job
	2. Parse file
	3. Extract fields
	4. Persist results
	5. Mark complete
	"""
	session: AsyncSession | None = None

	try:
		session = await _get_db_session()

		# 1. Load document and job from DB
		docs_repo = DocumentsRepository()
		jobs_repo = JobsRepository()

		document = await docs_repo.get_by_id(session, document_id)
		if not document:
			raise ValueError(f"Document not found: {document_id}")

		job = await jobs_repo.get_by_id(session, job_id)
		if not job:
			raise ValueError(f"Job not found: {job_id}")

		logger.info(
			"Processing document started",
			extra={
				"job_id": job_id,
				"document_id": document_id,
				"original_filename": document.original_filename,
			},
		)

		# 2. Mark job as PROCESSING and emit initial progress
		await _emit_progress(
			session,
			job_id,
			document_id,
			DocumentStatus.PROCESSING,
			JobStage.JOB_STARTED,
			10,
			"Job started",
		)

		# 3. Parse document
		await _emit_progress(
			session,
			job_id,
			document_id,
			DocumentStatus.PROCESSING,
			JobStage.DOCUMENT_PARSING_STARTED,
			20,
			"Parsing document",
		)

		try:
			parsed = parse_stage(
				file_path=document.storage_path,
				mime_type=document.mime_type,
				extension=document.extension,
			)
		except UnsupportedFileTypeError as exc:
			raise PermanentParseError(f"Unsupported file type: {exc}") from exc

		await _emit_progress(
			session,
			job_id,
			document_id,
			DocumentStatus.PROCESSING,
			JobStage.DOCUMENT_PARSING_COMPLETED,
			40,
			"Document parsed",
		)

		logger.info(
			"Document parsed",
			extra={
				"job_id": job_id,
				"chars": parsed.char_count,
				"lines": parsed.line_count,
			},
		)

		# 4. Extract fields
		await _emit_progress(
			session,
			job_id,
			document_id,
			DocumentStatus.PROCESSING,
			JobStage.FIELD_EXTRACTION_STARTED,
			55,
			"Extracting fields",
		)

		extracted = extract_stage(
			parsed=parsed,
			original_filename=document.original_filename,
			size_bytes=document.size_bytes,
		)

		await _emit_progress(
			session,
			job_id,
			document_id,
			DocumentStatus.PROCESSING,
			JobStage.FIELD_EXTRACTION_COMPLETED,
			75,
			"Fields extracted",
		)

		logger.info(
			"Fields extracted",
			extra={
				"job_id": job_id,
				"title": extracted.title,
				"category": extracted.category,
			},
		)

		# 5. Persist results
		await _emit_progress(
			session,
			job_id,
			document_id,
			DocumentStatus.PROCESSING,
			JobStage.RESULT_PERSIST_STARTED,
			85,
			"Persisting results",
		)

		await persist_stage(
			session=session,
			document_id=document_id,
			extracted=extracted,
		)

		await _emit_progress(
			session,
			job_id,
			document_id,
			DocumentStatus.PROCESSING,
			JobStage.RESULT_PERSIST_COMPLETED,
			95,
			"Results persisted",
		)

		# 6. Mark job and document as completed
		await _emit_progress(
			session,
			job_id,
			document_id,
			DocumentStatus.COMPLETED,
			JobStage.JOB_COMPLETED,
			100,
			"Job completed successfully",
		)

		# Update document status
		await docs_repo.update_status(session, document_id, DocumentStatus.COMPLETED)
		await session.commit()

		logger.info(
			"Processing document completed",
			extra={
				"job_id": job_id,
				"document_id": document_id,
			},
		)

	except PermanentParseError as exc:
		logger.error(
			"Permanent parsing error",
			extra={"job_id": job_id, "error": str(exc)},
		)
		if session:
			try:
				await _emit_progress(
					session,
					job_id,
					document_id,
					DocumentStatus.FAILED,
					JobStage.JOB_FAILED,
					0,
					f"Parsing failed: {str(exc)}",
				)
				docs_repo = DocumentsRepository()
				await docs_repo.update_status(session, document_id, DocumentStatus.FAILED)
				await session.commit()
			except Exception:
				logger.exception("Error marking job as failed")
				await session.rollback()
		raise

	except TransientParseError as exc:
		logger.warning(
			"Transient parsing error (retryable)",
			extra={"job_id": job_id, "error": str(exc)},
		)
		if session:
			try:
				await _emit_progress(
					session,
					job_id,
					document_id,
					DocumentStatus.PROCESSING,
					JobStage.JOB_RETRY_SCHEDULED,
					job.progress_percent or 0,
					f"Retrying: {str(exc)}",
				)
				await session.commit()
			except Exception:
				logger.exception("Error recording retry")
				await session.rollback()
		raise

	except Exception as exc:
		logger.exception(
			"Unexpected error during processing",
			extra={"job_id": job_id, "document_id": document_id},
		)
		if session:
			try:
				await _emit_progress(
					session,
					job_id,
					document_id,
					DocumentStatus.FAILED,
					JobStage.JOB_FAILED,
					0,
					f"Error: {str(exc)[:200]}",
				)
				docs_repo = DocumentsRepository()
				await docs_repo.update_status(session, document_id, DocumentStatus.FAILED)
				await session.commit()
			except Exception:
				logger.exception("Error marking job as failed")
				await session.rollback()
		raise

	finally:
		if session:
			await session.close()


@celery_app.task(
	bind=True,
	autoretry_for=(TransientParseError,),
	retry_backoff=True,
	retry_jitter=True,
	retry_kwargs={"max_retries": 3},
	default_retry_delay=60,
)
def process_document(self: Any, job_id: str, document_id: str) -> None:
	"""
	Celery task: Process an uploaded document through the pipeline.

	Args:
	    job_id: Processing job ID (UUID string)
	    document_id: Document ID (UUID string)

	Raises:
	    TransientParseError: Retryable error (will auto-retry)
	    PermanentParseError: Non-retryable error
	    Any other exception: Marked as failed in DB
	"""
	logger.info(
		"process_document task started",
		extra={
			"job_id": job_id,
			"document_id": document_id,
			"attempt": self.request.retries,
		},
	)

	try:
		# Run async processing in Celery sync context
		asyncio.run(_process_document_async(job_id, document_id))
	except Exception as exc:
		logger.error(
			"process_document task failed",
			extra={
				"job_id": job_id,
				"error": str(exc),
				"attempt": self.request.retries,
			},
		)
		raise
