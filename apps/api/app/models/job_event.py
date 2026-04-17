from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
	from app.models.processing_job import ProcessingJob


JSON_TYPE = sa.JSON().with_variant(JSONB, "postgresql")


class JobEvent(Base):
	__tablename__ = "job_events"
	__table_args__ = (
		sa.Index("ix_job_events_job_id_created_at_asc", "job_id", "created_at"),
	)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	job_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
		nullable=False,
	)
	event_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
	payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()
	)

	job: Mapped["ProcessingJob"] = relationship(back_populates="events")
