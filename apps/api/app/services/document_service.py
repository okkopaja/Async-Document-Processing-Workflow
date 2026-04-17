from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from celery import Celery
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.constants import DocumentStatus, JobStage
from app.integrations.storage import StorageService, StorageValidationError
from app.models.processing_job import ProcessingJob
from app.repositories.documents import DocumentsRepository
from app.repositories.events import EventsRepository
from app.repositories.jobs import JobsRepository
from app.schemas.document import DocumentUploadResponse
from app.workers.tasks.process_document import process_document


logger = logging.getLogger(__name__)


class DocumentUploadError(Exception):
	def __init__(self, code: str, message: str, status_code: int) -> None:
		super().__init__(message)
		self.code = code
		self.message = message
		self.status_code = status_code


class DocumentDeleteError(Exception):
	def __init__(self, code: str, message: str, status_code: int) -> None:
		super().__init__(message)
		self.code = code
		self.message = message
		self.status_code = status_code


class DocumentService:
	def __init__(
		self,
		storage_service: StorageService,
		task_client: Celery | None = None,
		documents_repo: DocumentsRepository | None = None,
		jobs_repo: JobsRepository | None = None,
		events_repo: EventsRepository | None = None,
	) -> None:
		self.storage_service = storage_service
		self.task_client = task_client or celery_app
		self.documents_repo = documents_repo or DocumentsRepository()
		self.jobs_repo = jobs_repo or JobsRepository()
		self.events_repo = events_repo or EventsRepository()

	async def upload_documents(
		self,
		session: AsyncSession,
		files: Sequence[UploadFile],
	) -> list[DocumentUploadResponse]:
		if not files:
			raise DocumentUploadError(
				code="VALIDATION_ERROR",
				message="At least one file is required.",
				status_code=422,
			)

		responses: list[DocumentUploadResponse] = []
		dispatch_queue: list[tuple[uuid.UUID, uuid.UUID]] = []

		try:
			for upload in files:
				if not upload.filename:
					raise DocumentUploadError(
						code="VALIDATION_ERROR",
						message="Each uploaded file must have a filename.",
						status_code=422,
					)

				payload = await upload.read()

				try:
					document_id = uuid.uuid4()
					stored_file = self.storage_service.save_upload(
						file_bytes=payload,
						document_id=str(document_id),
						original_name=upload.filename,
						content_type=upload.content_type,
					)
				except StorageValidationError as exc:
					raise DocumentUploadError(
						code=exc.code,
						message=exc.message,
						status_code=exc.status_code,
					) from exc

				document = await self.documents_repo.create(
					session,
					{
						"id": document_id,
						"original_filename": stored_file.original_filename,
						"stored_filename": stored_file.stored_filename,
						"mime_type": stored_file.mime_type,
						"extension": stored_file.extension,
						"size_bytes": stored_file.size_bytes,
						"storage_path": stored_file.storage_path,
						"status": DocumentStatus.QUEUED.value,
					},
				)

				job_id = uuid.uuid4()
				job = await self.jobs_repo.create(
					session,
					{
						"id": job_id,
						"document_id": document.id,
						"status": DocumentStatus.QUEUED.value,
						"current_stage": JobStage.JOB_QUEUED.value,
						"progress_percent": 0,
						"attempt_number": 1,
						"queued_at": datetime.now(timezone.utc),
					},
				)

				await self.events_repo.create(
					session,
					job_id=job.id,
					event_type=JobStage.DOCUMENT_RECEIVED.value,
					payload={
						"filename": document.original_filename,
						"status": document.status,
					},
				)

				await self.documents_repo.update_latest_job(session, doc_id=document.id, job_id=job.id)
				dispatch_queue.append((job.id, document.id))

				responses.append(
					DocumentUploadResponse(
						documentId=document.id,
						jobId=job.id,
						filename=document.original_filename,
						status=job.status,
					)
				)

			await session.commit()

		except DocumentUploadError:
			await session.rollback()
			raise
		except Exception as exc:
			await session.rollback()
			raise DocumentUploadError(
				code="PERSISTENCE_ERROR",
				message="Failed to store upload metadata and queue processing.",
				status_code=500,
			) from exc

		has_task_id_updates = False
		for job_id, document_id in dispatch_queue:
			task_id = self._dispatch_processing_task(job_id=job_id, document_id=document_id)
			if not task_id:
				continue

			updated_job = await self.jobs_repo.set_celery_task_id(
				session=session,
				job_id=job_id,
				celery_task_id=task_id,
			)
			has_task_id_updates = has_task_id_updates or bool(updated_job)

		if has_task_id_updates:
			try:
				await session.commit()
			except Exception:
				await session.rollback()
				logger.exception("Failed to persist Celery task IDs after upload commit")

		return responses

	async def delete_document(self, session: AsyncSession, document_id: uuid.UUID) -> None:
		document = await self.documents_repo.get_by_id(session, document_id)
		if not document:
			raise DocumentDeleteError(
				code="DOCUMENT_NOT_FOUND",
				message=f"Document not found: {document_id}",
				status_code=404,
			)

		jobs = await self.jobs_repo.list_for_document(session=session, doc_id=document_id)
		self._revoke_processing_tasks(jobs)

		try:
			self.storage_service.delete_document_artifacts(
				document_id=str(document_id),
				storage_path=document.storage_path,
			)
		except StorageValidationError as exc:
			raise DocumentDeleteError(
				code=exc.code,
				message=exc.message,
				status_code=exc.status_code,
			) from exc
		except Exception as exc:
			raise DocumentDeleteError(
				code="STORAGE_DELETE_ERROR",
				message="Failed to delete document files from storage.",
				status_code=500,
			) from exc

		try:
			deleted = await self.documents_repo.delete(session, document_id)
			if not deleted:
				raise DocumentDeleteError(
					code="DOCUMENT_NOT_FOUND",
					message=f"Document not found: {document_id}",
					status_code=404,
				)

			await session.commit()
		except DocumentDeleteError:
			await session.rollback()
			raise
		except Exception as exc:
			await session.rollback()
			raise DocumentDeleteError(
				code="PERSISTENCE_ERROR",
				message="Failed to delete document metadata.",
				status_code=500,
			) from exc

	def _revoke_processing_tasks(self, jobs: Sequence[ProcessingJob]) -> None:
		for job in jobs:
			if not job.celery_task_id:
				continue

			if job.status not in {DocumentStatus.QUEUED.value, DocumentStatus.PROCESSING.value}:
				continue

			try:
				self.task_client.control.revoke(job.celery_task_id, terminate=True)
			except Exception:
				logger.exception(
					"Failed to revoke Celery task during document deletion",
					extra={"job_id": str(job.id), "task_id": job.celery_task_id},
				)

	def _dispatch_processing_task(self, job_id: uuid.UUID, document_id: uuid.UUID) -> str | None:
		"""Dispatch document processing task to Celery worker."""
		try:
			# Use .delay() to queue the task asynchronously
			async_result = process_document.delay(str(job_id), str(document_id))
			return async_result.id
		except Exception:
			# Queue dispatch is best-effort; upload persistence remains testable
			# even if task dispatch fails
			return None
