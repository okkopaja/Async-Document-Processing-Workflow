from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.documents import DocumentsRepository
from app.repositories.results import ResultsRepository


class ExportServiceError(Exception):
	def __init__(self, code: str, message: str, status_code: int) -> None:
		super().__init__(message)
		self.code = code
		self.message = message
		self.status_code = status_code


class ExportService:
	def __init__(
		self,
		results_repo: ResultsRepository | None = None,
		documents_repo: DocumentsRepository | None = None,
	) -> None:
		self.results_repo = results_repo or ResultsRepository()
		self.documents_repo = documents_repo or DocumentsRepository()

	async def export_json(
		self,
		session: AsyncSession,
		doc_id: uuid.UUID,
	) -> dict[str, Any]:
		"""
		Export finalized document result as JSON.

		Per design doc §23.1:
		Returns structured JSON with keys:
		- documentId, filename, title, category, summary, keywords, status, finalizedAt, structuredJson
		"""
		# Get document
		document = await self.documents_repo.get_by_id(session, doc_id)
		if not document:
			raise ExportServiceError(
				code="DOCUMENT_NOT_FOUND",
				message=f"Document {doc_id} not found",
				status_code=404,
			)

		# Get result
		result = await self.results_repo.get_by_document_id(session, doc_id)
		if not result:
			raise ExportServiceError(
				code="EXPORT_NOT_ALLOWED",
				message=f"No result exists for document {doc_id}",
				status_code=400,
			)

		# Validate finalized
		if not result.is_finalized:
			raise ExportServiceError(
				code="EXPORT_NOT_ALLOWED",
				message="Result must be finalized before export",
				status_code=400,
			)

		# Build export
		return {
			"documentId": str(document.id),
			"filename": document.original_filename,
			"title": result.title,
			"category": result.category,
			"summary": result.summary,
			"keywords": result.keywords_json or [],
			"status": document.status,
			"finalizedAt": result.finalized_at.isoformat() if result.finalized_at else None,
			"structuredJson": result.structured_json or {},
		}

	async def export_csv(
		self,
		session: AsyncSession,
		doc_id: uuid.UUID,
	) -> str:
		"""
		Export finalized document result as CSV.

		Per design doc §23.2:
		Columns: document_id, filename, title, category, summary, keywords, status, finalized_at
		Returns CSV string.
		"""
		# Get document
		document = await self.documents_repo.get_by_id(session, doc_id)
		if not document:
			raise ExportServiceError(
				code="DOCUMENT_NOT_FOUND",
				message=f"Document {doc_id} not found",
				status_code=404,
			)

		# Get result
		result = await self.results_repo.get_by_document_id(session, doc_id)
		if not result:
			raise ExportServiceError(
				code="EXPORT_NOT_ALLOWED",
				message=f"No result exists for document {doc_id}",
				status_code=400,
			)

		# Validate finalized
		if not result.is_finalized:
			raise ExportServiceError(
				code="EXPORT_NOT_ALLOWED",
				message="Result must be finalized before export",
				status_code=400,
			)

		# Build CSV
		output = io.StringIO()
		writer = csv.DictWriter(
			output,
			fieldnames=[
				"document_id",
				"filename",
				"title",
				"category",
				"summary",
				"keywords",
				"status",
				"finalized_at",
			],
		)
		writer.writeheader()
		writer.writerow(
			{
				"document_id": str(document.id),
				"filename": document.original_filename,
				"title": result.title or "",
				"category": result.category or "",
				"summary": result.summary or "",
				"keywords": json.dumps(result.keywords_json or []),
				"status": document.status,
				"finalized_at": result.finalized_at.isoformat() if result.finalized_at else "",
			}
		)
		return output.getvalue()
