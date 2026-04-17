"""Review and finalization service for document results."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DocumentStatus
from app.models.document_result import DocumentResult
from app.repositories.documents import DocumentsRepository
from app.repositories.results import ResultsRepository

logger = logging.getLogger(__name__)


class ReviewService:
	"""Service for reviewing, editing, and finalizing document results."""

	def __init__(self):
		"""Initialize the review service."""
		self.docs_repo = DocumentsRepository()
		self.results_repo = ResultsRepository()

	async def update_result(
		self,
		session: AsyncSession,
		document_id: str,
		update_data: dict[str, Any],
		expected_version: int,
	) -> DocumentResult:
		"""
		Update editable fields of a document result.

		Editable fields: title, category, summary, keywords

		Args:
			session: Async DB session
			document_id: Document UUID string
			update_data: Dict with fields to update
			expected_version: Current result version (optimistic concurrency check)

		Returns:
			Updated DocumentResult

		Raises:
			ValueError: If document not found, result not found, already finalized,
					   or version mismatch
		"""
		# 1. Validate document exists
		document = await self.docs_repo.get_by_id(session, document_id)
		if not document:
			raise ValueError(f"Document not found: {document_id}")

		# 2. Get current result
		result = await self.results_repo.get_by_document_id(session, document_id)
		if not result:
			raise ValueError(f"No result found for document: {document_id}")

		# 3. Validate not already finalized
		if result.is_finalized:
			raise ValueError(f"Cannot edit finalized result for document: {document_id}")

		# 4. Check optimistic concurrency (version match)
		if result.version != expected_version:
			raise ValueError(
				f"Version mismatch: expected {expected_version}, got {result.version}"
			)

		# 5. Update only editable fields
		editable_fields = {"title", "category", "summary", "keywords_json"}
		for field, value in update_data.items():
			if field in editable_fields:
				if field == "keywords_json":
					setattr(result, field, value if isinstance(value, list) else [])
				else:
					setattr(result, field, value)

		# 6. Increment version and update timestamp
		result.version += 1
		await session.flush()

		logger.info(
			"Result updated",
			extra={
				"document_id": document_id,
				"new_version": result.version,
				"updated_fields": list(update_data.keys()),
			},
		)

		return result

	async def finalize_result(
		self,
		session: AsyncSession,
		document_id: str,
		expected_version: int,
	) -> DocumentResult:
		"""
		Finalize a document result.

		Sets is_finalized=True and finalized_at=now().
		Document status is updated to FINALIZED.

		Args:
			session: Async DB session
			document_id: Document UUID string
			expected_version: Current result version (optimistic concurrency check)

		Returns:
			Finalized DocumentResult

		Raises:
			ValueError: If document not found, result not found, document not COMPLETED,
					   or version mismatch
		"""
		# 1. Validate document exists and is COMPLETED
		document = await self.docs_repo.get_by_id(session, document_id)
		if not document:
			raise ValueError(f"Document not found: {document_id}")

		if document.status != DocumentStatus.COMPLETED:
			raise ValueError(
				f"Cannot finalize document not in COMPLETED status: {document.status}"
			)

		# 2. Get current result
		result = await self.results_repo.get_by_document_id(session, document_id)
		if not result:
			raise ValueError(f"No result found for document: {document_id}")

		# 3. Check optimistic concurrency (version match)
		if result.version != expected_version:
			raise ValueError(
				f"Version mismatch: expected {expected_version}, got {result.version}"
			)

		# 4. Finalize result
		result.is_finalized = True
		await session.flush()

		# 5. Update document status to FINALIZED
		await self.docs_repo.update_status(session, document_id, DocumentStatus.FINALIZED)

		logger.info(
			"Result finalized",
			extra={
				"document_id": document_id,
				"version": result.version,
			},
		)

		return result


def get_review_service() -> ReviewService:
	"""Get a configured review service instance."""
	return ReviewService()
