from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
	from app.models.document import Document
	from app.models.job_event import JobEvent


class ProcessingJob(Base):
	__tablename__ = "processing_jobs"
	__table_args__ = (
		sa.Index(
			"ix_processing_jobs_document_id_created_at_desc",
			"document_id",
			sa.text("created_at DESC"),
		),
		sa.UniqueConstraint("celery_task_id", name="uq_processing_jobs_celery_task_id"),
	)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	document_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		sa.ForeignKey("documents.id", ondelete="CASCADE"),
		nullable=False,
	)
	celery_task_id: Mapped[str | None] = mapped_column(sa.String(256), nullable=True)
	status: Mapped[str] = mapped_column(
		sa.String(32), nullable=False, default="QUEUED", server_default=sa.text("'QUEUED'")
	)
	current_stage: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
	progress_percent: Mapped[int] = mapped_column(
		sa.Integer, nullable=False, default=0, server_default=sa.text("0")
	)
	attempt_number: Mapped[int] = mapped_column(
		sa.Integer, nullable=False, default=1, server_default=sa.text("1")
	)
	error_code: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
	error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
	queued_at: Mapped[datetime] = mapped_column(
		sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()
	)
	started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
	finished_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()
	)
	updated_at: Mapped[datetime] = mapped_column(
		sa.DateTime(timezone=True),
		nullable=False,
		server_default=sa.func.current_timestamp(),
		onupdate=sa.func.current_timestamp(),
	)

	document: Mapped["Document"] = relationship(
		back_populates="jobs",
		foreign_keys=[document_id],
	)
	events: Mapped[list["JobEvent"]] = relationship(
		back_populates="job",
		cascade="all, delete-orphan",
	)
