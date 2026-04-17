from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processing_job import ProcessingJob


class JobsRepository:
	async def create(self, session: AsyncSession, data: dict[str, Any]) -> ProcessingJob:
		job = ProcessingJob(**data)
		session.add(job)
		await session.flush()
		return job

	async def get_by_id(self, session: AsyncSession, job_id: uuid.UUID) -> ProcessingJob | None:
		result = await session.execute(sa.select(ProcessingJob).where(ProcessingJob.id == job_id))
		return result.scalar_one_or_none()

	async def get_latest_for_document(
		self, session: AsyncSession, doc_id: uuid.UUID
	) -> ProcessingJob | None:
		result = await session.execute(
			sa.select(ProcessingJob)
			.where(ProcessingJob.document_id == doc_id)
			.order_by(ProcessingJob.created_at.desc())
			.limit(1)
		)
		return result.scalar_one_or_none()

	async def list_for_document(
		self,
		session: AsyncSession,
		doc_id: uuid.UUID,
	) -> list[ProcessingJob]:
		result = await session.execute(
			sa.select(ProcessingJob)
			.where(ProcessingJob.document_id == doc_id)
			.order_by(ProcessingJob.created_at.desc())
		)
		return list(result.scalars().all())

	async def set_celery_task_id(
		self,
		session: AsyncSession,
		job_id: uuid.UUID,
		celery_task_id: str,
	) -> ProcessingJob | None:
		job = await self.get_by_id(session, job_id)
		if not job:
			return None

		job.celery_task_id = celery_task_id
		await session.flush()
		return job

	async def update_status(
		self,
		session: AsyncSession,
		job_id: uuid.UUID,
		status: str,
		stage: str | None,
		progress: int | None,
		**kwargs: Any,
	) -> ProcessingJob | None:
		job = await self.get_by_id(session, job_id)
		if not job:
			return None

		job.status = status
		job.current_stage = stage
		if progress is not None:
			job.progress_percent = progress

		for key, value in kwargs.items():
			if hasattr(job, key):
				setattr(job, key, value)

		await session.flush()
		return job

	async def mark_started(self, session: AsyncSession, job_id: uuid.UUID) -> ProcessingJob | None:
		return await self.update_status(
			session,
			job_id,
			status="PROCESSING",
			stage="job_started",
			progress=10,
			started_at=datetime.now(timezone.utc),
		)

	async def mark_completed(self, session: AsyncSession, job_id: uuid.UUID) -> ProcessingJob | None:
		return await self.update_status(
			session,
			job_id,
			status="COMPLETED",
			stage="job_completed",
			progress=100,
			finished_at=datetime.now(timezone.utc),
		)

	async def mark_failed(
		self,
		session: AsyncSession,
		job_id: uuid.UUID,
		error_code: str,
		error_message: str,
	) -> ProcessingJob | None:
		return await self.update_status(
			session,
			job_id,
			status="FAILED",
			stage="job_failed",
			progress=100,
			error_code=error_code,
			error_message=error_message,
			finished_at=datetime.now(timezone.utc),
		)
