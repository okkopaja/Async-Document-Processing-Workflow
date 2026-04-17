from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_result import DocumentResult
from app.models.processing_job import ProcessingJob


class DocumentsRepository:
	async def create(self, session: AsyncSession, data: dict[str, Any]) -> Document:
		document = Document(**data)
		session.add(document)
		await session.flush()
		return document

	async def get_by_id(self, session: AsyncSession, doc_id: uuid.UUID) -> Document | None:
		result = await session.execute(sa.select(Document).where(Document.id == doc_id))
		return result.scalar_one_or_none()

	async def list_documents(
		self,
		session: AsyncSession,
		filters: dict[str, Any] | None = None,
		pagination: dict[str, int] | None = None,
		sort: dict[str, str] | None = None,
	) -> tuple[list[Document], int]:
		filters = filters or {}
		pagination = pagination or {}
		sort = sort or {}

		page = max(int(pagination.get("page", 1)), 1)
		page_size = min(max(int(pagination.get("page_size", 20)), 1), 100)

		stmt = sa.select(Document)

		if filters.get("status"):
			stmt = stmt.where(Document.status == filters["status"])

		search_term = filters.get("search")
		if search_term:
			like = f"%{search_term}%"
			stmt = stmt.outerjoin(DocumentResult, DocumentResult.document_id == Document.id).where(
				sa.or_(
					Document.original_filename.ilike(like),
					DocumentResult.title.ilike(like),
					DocumentResult.category.ilike(like),
				)
			)

		sort_by = sort.get("sort_by", "created_at")
		sort_order = sort.get("sort_order", "desc").lower()

		if sort_by == "progress_percent":
			stmt = stmt.outerjoin(ProcessingJob, ProcessingJob.id == Document.latest_job_id)
			order_column = ProcessingJob.progress_percent
		else:
			order_column = {
				"created_at": Document.created_at,
				"original_filename": Document.original_filename,
				"status": Document.status,
			}.get(sort_by, Document.created_at)

		order_clause = order_column.asc() if sort_order == "asc" else order_column.desc()
		stmt = stmt.order_by(order_clause)

		count_stmt = sa.select(sa.func.count()).select_from(stmt.order_by(None).subquery())
		total = int((await session.execute(count_stmt)).scalar_one())

		stmt = stmt.offset((page - 1) * page_size).limit(page_size)
		items = list((await session.execute(stmt)).scalars().all())
		return items, total

	async def update_status(
		self, session: AsyncSession, doc_id: uuid.UUID, status: str
	) -> Document | None:
		document = await self.get_by_id(session, doc_id)
		if not document:
			return None
		document.status = status
		await session.flush()
		return document

	async def update_latest_job(
		self, session: AsyncSession, doc_id: uuid.UUID, job_id: uuid.UUID
	) -> Document | None:
		document = await self.get_by_id(session, doc_id)
		if not document:
			return None
		document.latest_job_id = job_id
		await session.flush()
		return document

	async def delete(self, session: AsyncSession, doc_id: uuid.UUID) -> bool:
		document = await self.get_by_id(session, doc_id)
		if not document:
			return False

		await session.delete(document)
		await session.flush()
		return True
