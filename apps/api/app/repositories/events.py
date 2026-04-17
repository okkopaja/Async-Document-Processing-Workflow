from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_event import JobEvent


class EventsRepository:
	async def create(
		self,
		session: AsyncSession,
		job_id: uuid.UUID,
		event_type: str,
		payload: dict[str, Any] | None,
	) -> JobEvent:
		event = JobEvent(job_id=job_id, event_type=event_type, payload_json=payload)
		session.add(event)
		await session.flush()
		return event

	async def list_for_job(self, session: AsyncSession, job_id: uuid.UUID) -> list[JobEvent]:
		result = await session.execute(
			sa.select(JobEvent)
			.where(JobEvent.job_id == job_id)
			.order_by(JobEvent.created_at.asc())
		)
		return list(result.scalars().all())
