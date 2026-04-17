"""Result persistence stage — write extracted data to database."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_result import DocumentResult
from app.repositories.results import ResultsRepository
from app.workers.pipelines.extract_stage import ExtractedResult


async def persist_stage(
	session: AsyncSession,
	document_id: str,
	extracted: ExtractedResult,
) -> DocumentResult:
	"""
	Persist extracted fields to document_results table.

	Args:
	    session: Async DB session
	    document_id: Document ID (UUID)
	    extracted: ExtractedResult from extract_stage

	Returns:
	    Updated DocumentResult row
	"""
	results_repo = ResultsRepository()

	# Upsert document_results row
	result = await results_repo.create_or_update(
		session=session,
		doc_id=document_id,
		data={
			"title": extracted.title,
			"category": extracted.category,
			"summary": extracted.summary,
			"keywords_json": extracted.keywords,
			"raw_text": extracted.raw_text,
			"structured_json": extracted.structured_json,
			"is_finalized": False,
			"version": 1,
		},
	)

	return result
