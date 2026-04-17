from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_result import DocumentResult


class VersionConflictError(Exception):
	pass


class ResultsRepository:
	async def create_or_update(
		self, session: AsyncSession, doc_id: uuid.UUID, data: dict[str, Any]
	) -> DocumentResult:
		existing = await self.get_by_document_id(session, doc_id)
		if existing:
			for key, value in data.items():
				if hasattr(existing, key):
					setattr(existing, key, value)
			await session.flush()
			return existing

		result = DocumentResult(document_id=doc_id, **data)
		session.add(result)
		await session.flush()
		return result

	async def get_by_document_id(
		self, session: AsyncSession, doc_id: uuid.UUID
	) -> DocumentResult | None:
		result = await session.execute(
			sa.select(DocumentResult).where(DocumentResult.document_id == doc_id)
		)
		return result.scalar_one_or_none()

	async def update_fields(
		self,
		session: AsyncSession,
		doc_id: uuid.UUID,
		fields: dict[str, Any],
		expected_version: int,
	) -> DocumentResult:
		result = await self.get_by_document_id(session, doc_id)
		if not result:
			raise ValueError("Result not found")
		if result.version != expected_version:
			raise VersionConflictError("Version mismatch")

		for key, value in fields.items():
			if hasattr(result, key):
				setattr(result, key, value)

		result.version += 1
		await session.flush()
		return result

	async def finalize(
		self, session: AsyncSession, doc_id: uuid.UUID, expected_version: int
	) -> DocumentResult:
		result = await self.get_by_document_id(session, doc_id)
		if not result:
			raise ValueError("Result not found")
		if result.version != expected_version:
			raise VersionConflictError("Version mismatch")

		result.is_finalized = True
		result.finalized_at = datetime.now(timezone.utc)
		result.version += 1
		await session.flush()
		return result
