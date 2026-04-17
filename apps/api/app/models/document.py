from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
	from app.models.document_result import DocumentResult
	from app.models.processing_job import ProcessingJob


class Document(Base):
	__tablename__ = "documents"
	__table_args__ = (
		sa.Index("ix_documents_status_created_at_desc", "status", sa.text("created_at DESC")),
		sa.Index("ix_documents_original_filename", "original_filename"),
	)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	original_filename: Mapped[str] = mapped_column(sa.String(512), nullable=False)
	stored_filename: Mapped[str] = mapped_column(sa.String(512), nullable=False)
	mime_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
	extension: Mapped[str] = mapped_column(sa.String(16), nullable=False)
	size_bytes: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
	storage_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
	status: Mapped[str] = mapped_column(
		sa.String(32), nullable=False, default="QUEUED", server_default=sa.text("'QUEUED'")
	)
	created_at: Mapped[datetime] = mapped_column(
		sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()
	)
	updated_at: Mapped[datetime] = mapped_column(
		sa.DateTime(timezone=True),
		nullable=False,
		server_default=sa.func.current_timestamp(),
		onupdate=sa.func.current_timestamp(),
	)
	latest_job_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True),
		sa.ForeignKey("processing_jobs.id", use_alter=True, name="fk_documents_latest_job_id"),
		nullable=True,
	)

	jobs: Mapped[list["ProcessingJob"]] = relationship(
		back_populates="document",
		foreign_keys="ProcessingJob.document_id",
		cascade="all, delete-orphan",
	)
	latest_job: Mapped["ProcessingJob | None"] = relationship(
		foreign_keys=[latest_job_id],
		post_update=True,
	)
	result: Mapped["DocumentResult | None"] = relationship(
		back_populates="document",
		uselist=False,
		cascade="all, delete-orphan",
	)
