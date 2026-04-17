from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
	from app.models.document import Document


JSON_TYPE = sa.JSON().with_variant(JSONB, "postgresql")


class DocumentResult(Base):
	__tablename__ = "document_results"
	__table_args__ = (
		sa.UniqueConstraint("document_id", name="uq_document_results_document_id"),
	)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	document_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		sa.ForeignKey("documents.id", ondelete="CASCADE"),
		nullable=False,
		unique=True,
	)
	title: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
	category: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
	summary: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
	keywords_json: Mapped[list[str]] = mapped_column(
		JSON_TYPE, nullable=False, default=list, server_default=sa.text("'[]'")
	)
	raw_text: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
	structured_json: Mapped[dict[str, Any]] = mapped_column(
		JSON_TYPE, nullable=False, default=dict, server_default=sa.text("'{}'")
	)
	is_finalized: Mapped[bool] = mapped_column(
		sa.Boolean, nullable=False, default=False, server_default=sa.text("false")
	)
	finalized_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()
	)
	updated_at: Mapped[datetime] = mapped_column(
		sa.DateTime(timezone=True),
		nullable=False,
		server_default=sa.func.current_timestamp(),
		onupdate=sa.func.current_timestamp(),
	)
	version: Mapped[int] = mapped_column(
		sa.Integer, nullable=False, default=1, server_default=sa.text("1")
	)

	document: Mapped["Document"] = relationship(back_populates="result")
