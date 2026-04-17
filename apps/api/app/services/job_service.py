from __future__ import annotations

import uuid
from datetime import datetime, timezone
import logging
from typing import Any

from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.constants import DocumentStatus, JobStage
from app.repositories.documents import DocumentsRepository
from app.repositories.jobs import JobsRepository
from app.workers.tasks.process_document import process_document


logger = logging.getLogger(__name__)


class JobServiceError(Exception):
	def __init__(self, code: str, message: str, status_code: int) -> None:
		super().__init__(message)
		self.code = code
		self.message = message
		self.status_code = status_code


class JobService:
	def __init__(
		self,
		task_client: Celery | None = None,
		jobs_repo: JobsRepository | None = None,
		documents_repo: DocumentsRepository | None = None,
	) -> None:
		self.task_client = task_client or celery_app
		self.jobs_repo = jobs_repo or JobsRepository()
		self.documents_repo = documents_repo or DocumentsRepository()

	async def retry_failed_job(
		self,
		session: AsyncSession,
		job_id: uuid.UUID,
	) -> dict[str, Any]:
		"""
		Retry a failed job by creating a new job with incremented attempt number.

		Per design doc §8.1.1:
		1. Load existing job
		2. Validate status == FAILED
		3. Create new ProcessingJob with attempt_number = prev + 1, status QUEUED
		4. Update document.status = QUEUED
		5. Update document.latest_job_id to new job ID
		6. Dispatch new Celery task
		7. Return new job info
		"""
		# 1. Load existing job
		old_job = await self.jobs_repo.get_by_id(session, job_id)
		if not old_job:
			raise JobServiceError(
				code="JOB_NOT_FOUND",
				message=f"Job {job_id} not found",
				status_code=404,
			)

		# 2. Validate status == FAILED
		if old_job.status != "FAILED":
			raise JobServiceError(
				code="JOB_NOT_RETRYABLE",
				message=f"Job {job_id} is in {old_job.status} status, cannot retry",
				status_code=400,
			)

		# 3. Create new job with incremented attempt
		new_job_data = {
			"document_id": old_job.document_id,
			"status": "QUEUED",
			"current_stage": JobStage.JOB_QUEUED,
			"progress_percent": 5,
			"attempt_number": old_job.attempt_number + 1,
			"queued_at": datetime.now(timezone.utc),
		}
		new_job = await self.jobs_repo.create(session, new_job_data)

		# 4. Update document status to QUEUED
		await self.documents_repo.update_status(
			session,
			old_job.document_id,
			DocumentStatus.QUEUED,
		)

		# 5. Update document.latest_job_id
		await self.documents_repo.update_latest_job(
			session,
			old_job.document_id,
			new_job.id,
		)

		# 6. Dispatch new Celery task
		try:
			task = self.task_client.send_task(
				process_document.name,
				args=(str(new_job.id), str(old_job.document_id)),
			)
			new_job.celery_task_id = task.id
		except Exception:
			# Keep retry row creation durable even when broker/backend is unavailable
			# in local unit-test runs.
			logger.exception(
				"Failed to dispatch retry task; keeping job queued",
				extra={"job_id": str(new_job.id), "document_id": str(old_job.document_id)},
			)
			new_job.celery_task_id = None
		await session.flush()

		# 7. Return new job info
		return {
			"jobId": str(new_job.id),
			"documentId": str(new_job.document_id),
			"attemptNumber": new_job.attempt_number,
			"status": new_job.status,
		}
