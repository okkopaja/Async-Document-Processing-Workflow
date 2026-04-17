from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, Query, Path, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_document_service
from app.schemas.common import PaginatedResponse
from app.schemas.document import (
	DocumentUploadBatchResponse,
	DocumentListItem,
	DocumentDetailResponse,
	DocumentDetailPayload,
	JobPayload,
	ResultPayload,
	EventPayload,
	DocumentResultUpdate,
	FinalizeRequest,
)
from app.services.document_service import DocumentService, DocumentDeleteError, DocumentUploadError
from app.services.review_service import get_review_service
from app.repositories.documents import DocumentsRepository
from app.repositories.jobs import JobsRepository
from app.repositories.results import ResultsRepository
from app.repositories.events import EventsRepository

logger = logging.getLogger(__name__)
router = APIRouter()


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
	return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


@router.post(
	"/upload",
	status_code=status.HTTP_202_ACCEPTED,
	response_model=DocumentUploadBatchResponse,
)
async def upload_documents(
	session: Annotated[AsyncSession, Depends(get_db_session)],
	document_service: Annotated[DocumentService, Depends(get_document_service)],
	files: Annotated[list[UploadFile] | None, File()] = None,
) -> DocumentUploadBatchResponse:
	if not files:
		return _error_response(
			code="VALIDATION_ERROR",
			message="At least one file is required.",
			status_code=422,
		)

	try:
		items = await document_service.upload_documents(session=session, files=files)
	except DocumentUploadError as exc:
		return _error_response(code=exc.code, message=exc.message, status_code=exc.status_code)

	return DocumentUploadBatchResponse(items=items)


@router.get("", response_model=PaginatedResponse[DocumentListItem])
async def list_documents(
	session: Annotated[AsyncSession, Depends(get_db_session)],
	search: Annotated[str | None, Query()] = None,
	status_filter: Annotated[str | None, Query(alias="status")] = None,
	sort_by: Annotated[str, Query()] = "created_at",
	sort_order: Annotated[str, Query()] = "desc",
	page: Annotated[int, Query(ge=1)] = 1,
	page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[DocumentListItem]:
	"""
	List documents with optional filtering, sorting, and pagination.

	Query Parameters:
	- search: Search in filename, title, category
	- status: Filter by status (QUEUED, PROCESSING, COMPLETED, FAILED, FINALIZED)
	- sort_by: Sort field (created_at, original_filename, status, progress_percent)
	- sort_order: asc or desc
	- page: Page number (1-indexed)
	- page_size: Items per page (1-100)
	"""
	try:
		docs_repo = DocumentsRepository()

		# Build filters
		filters = {}
		if status_filter:
			filters["status"] = status_filter
		if search:
			filters["search"] = search

		# List documents
		documents, total = await docs_repo.list_documents(
			session=session,
			filters=filters,
			pagination={"page": page, "page_size": page_size},
			sort={"sort_by": sort_by, "sort_order": sort_order},
		)

		# Convert to response items
		items = [
			DocumentListItem(
				document_id=doc.id,
				original_filename=doc.original_filename,
				mime_type=doc.mime_type,
				size_bytes=doc.size_bytes,
				status=doc.status,
				created_at=doc.created_at,
				latest_job_id=doc.latest_job_id,
				current_stage=None,
				progress_percent=None,  # Will be populated from job if available
			)
			for doc in documents
		]

		# Populate progress from latest jobs
		jobs_repo = JobsRepository()
		for item in items:
			if item.latest_job_id:
				job = await jobs_repo.get_by_id(session, item.latest_job_id)
				if job:
					item.progress_percent = job.progress_percent
					item.latest_job_status = job.status
					item.current_stage = job.current_stage

		return PaginatedResponse(
			items=items,
			page=page,
			pageSize=page_size,
			total=total,
		)

	except Exception:
		logger.exception("Error listing documents")
		raise


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document_detail(
	document_id: Annotated[UUID, Path()],
	session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentDetailResponse:
	"""
	Get detailed information about a document.

	Returns:
	- document: Document metadata
	- job: Latest processing job
	- result: Document result (if any)
	- events: All job events in chronological order
	"""
	try:
		docs_repo = DocumentsRepository()
		jobs_repo = JobsRepository()
		results_repo = ResultsRepository()
		events_repo = EventsRepository()

		# 1. Get document
		document = await docs_repo.get_by_id(session, document_id)
		if not document:
			return _error_response(
				code="DOCUMENT_NOT_FOUND",
				message=f"Document not found: {document_id}",
				status_code=404,
			)

		# Convert to Pydantic
		doc_payload = DocumentDetailPayload(
			id=document.id,
			original_filename=document.original_filename,
			mime_type=document.mime_type,
			extension=document.extension,
			size_bytes=document.size_bytes,
			status=document.status,
			created_at=document.created_at,
			updated_at=document.updated_at,
			latest_job_id=document.latest_job_id,
		)

		# 2. Get latest job
		job_payload = None
		job_events = []
		if document.latest_job_id:
			job = await jobs_repo.get_by_id(session, document.latest_job_id)
			if job:
				job_payload = JobPayload(
					id=job.id,
					status=job.status,
					current_stage=job.current_stage,
					progress_percent=job.progress_percent or 0,
					attempt_number=job.attempt_number,
					error_code=job.error_code,
					error_message=job.error_message,
					queued_at=job.queued_at,
					started_at=job.started_at,
					finished_at=job.finished_at,
				)
				# 4. Get events for this job
				job_events = await events_repo.list_for_job(session, job.id)

		# Convert events
		event_payloads = [
			EventPayload(
				id=evt.id,
				event_type=evt.event_type,
				payload_json=evt.payload_json,
				created_at=evt.created_at,
			)
			for evt in job_events
		]

		# 3. Get result
		result_payload = None
		result = await results_repo.get_by_document_id(session, document_id)
		if result:
			result_payload = ResultPayload(
				id=result.id,
				document_id=result.document_id,
				title=result.title,
				category=result.category,
				summary=result.summary,
				keywords=result.keywords_json or [],
				raw_text=result.raw_text,
				structured_json=result.structured_json or {},
				is_finalized=result.is_finalized,
				finalized_at=result.finalized_at,
				version=result.version,
			)

		return DocumentDetailResponse(
			document=doc_payload,
			job=job_payload,
			result=result_payload,
			events=event_payloads,
		)

	except Exception:
		logger.exception("Error getting document detail")
		return _error_response(
			code="INTERNAL_ERROR",
			message="Failed to retrieve document details",
			status_code=500,
		)



@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
	document_id: Annotated[UUID, Path()],
	session: Annotated[AsyncSession, Depends(get_db_session)],
	document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> Response:
	try:
		await document_service.delete_document(session=session, document_id=document_id)
	except DocumentDeleteError as exc:
		return _error_response(code=exc.code, message=exc.message, status_code=exc.status_code)

	return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{document_id}/result", response_model=DocumentDetailResponse)
async def update_document_result(
	document_id: Annotated[UUID, Path()],
	update_request: DocumentResultUpdate,
	session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentDetailResponse:
	"""
	Update editable fields of a document result.

	Editable fields: title, category, summary, keywords
	Uses optimistic concurrency (version field required).
	"""
	try:
		review_service = get_review_service()
		docs_repo = DocumentsRepository()
		jobs_repo = JobsRepository()
		results_repo = ResultsRepository()
		events_repo = EventsRepository()

		# Update result with version check
		update_data = {
			k: v for k, v in update_request.dict(exclude_unset=True).items()
			if k != "version"
		}

		await review_service.update_result(
			session=session,
			document_id=document_id,
			update_data=update_data,
			expected_version=update_request.version,
		)

		await session.commit()

		# Fetch and return updated detail (use detail endpoint logic)
		document = await docs_repo.get_by_id(session, document_id)
		if not document:
			return _error_response(
				code="DOCUMENT_NOT_FOUND",
				message=f"Document not found: {document_id}",
				status_code=404,
			)

		# Convert document
		doc_payload = DocumentDetailPayload(
			id=document.id,
			original_filename=document.original_filename,
			mime_type=document.mime_type,
			extension=document.extension,
			size_bytes=document.size_bytes,
			status=document.status,
			created_at=document.created_at,
			updated_at=document.updated_at,
			latest_job_id=document.latest_job_id,
		)

		job_payload = None
		job_events = []
		if document.latest_job_id:
			job = await jobs_repo.get_by_id(session, document.latest_job_id)
			if job:
				job_payload = JobPayload(
					id=job.id,
					status=job.status,
					current_stage=job.current_stage,
					progress_percent=job.progress_percent or 0,
					attempt_number=job.attempt_number,
					error_code=job.error_code,
					error_message=job.error_message,
					queued_at=job.queued_at,
					started_at=job.started_at,
					finished_at=job.finished_at,
				)
				job_events = await events_repo.list_for_job(session, job.id)

		event_payloads = [
			EventPayload(
				id=evt.id,
				event_type=evt.event_type,
				payload_json=evt.payload_json,
				created_at=evt.created_at,
			)
			for evt in job_events
		]

		result = await results_repo.get_by_document_id(session, document_id)
		result_payload = None
		if result:
			result_payload = ResultPayload(
				id=result.id,
				document_id=result.document_id,
				title=result.title,
				category=result.category,
				summary=result.summary,
				keywords=result.keywords_json or [],
				raw_text=result.raw_text,
				structured_json=result.structured_json or {},
				is_finalized=result.is_finalized,
				finalized_at=result.finalized_at,
				version=result.version,
			)

		return DocumentDetailResponse(
			document=doc_payload,
			job=job_payload,
			result=result_payload,
			events=event_payloads,
		)

	except ValueError as exc:
		error_msg = str(exc)
		if "Version mismatch" in error_msg:
			return _error_response(
				code="CONFLICT_VERSION_MISMATCH",
				message=error_msg,
				status_code=409,
			)
		elif "finalized" in error_msg.lower():
			return _error_response(
				code="EDIT_NOT_ALLOWED",
				message=error_msg,
				status_code=400,
			)
		else:
			return _error_response(
				code="VALIDATION_ERROR",
				message=error_msg,
				status_code=400,
			)
	except Exception:
		logger.exception("Error updating document result")
		return _error_response(
			code="INTERNAL_ERROR",
			message="Failed to update document result",
			status_code=500,
		)


@router.post("/{document_id}/finalize", response_model=DocumentDetailResponse)
async def finalize_document_result(
	document_id: Annotated[UUID, Path()],
	finalize_request: FinalizeRequest,
	session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentDetailResponse:
	"""
	Finalize a document result.

	Sets is_finalized=True and document status to FINALIZED.
	Uses optimistic concurrency (version field required).
	"""
	try:
		review_service = get_review_service()
		docs_repo = DocumentsRepository()
		jobs_repo = JobsRepository()
		results_repo = ResultsRepository()
		events_repo = EventsRepository()

		# Finalize result with version check
		await review_service.finalize_result(
			session=session,
			document_id=document_id,
			expected_version=finalize_request.version,
		)

		await session.commit()

		# Fetch and return updated detail
		document = await docs_repo.get_by_id(session, document_id)
		if not document:
			return _error_response(
				code="DOCUMENT_NOT_FOUND",
				message=f"Document not found: {document_id}",
				status_code=404,
			)

		# Convert document
		doc_payload = DocumentDetailPayload(
			id=document.id,
			original_filename=document.original_filename,
			mime_type=document.mime_type,
			extension=document.extension,
			size_bytes=document.size_bytes,
			status=document.status,
			created_at=document.created_at,
			updated_at=document.updated_at,
			latest_job_id=document.latest_job_id,
		)

		job_payload = None
		job_events = []
		if document.latest_job_id:
			job = await jobs_repo.get_by_id(session, document.latest_job_id)
			if job:
				job_payload = JobPayload(
					id=job.id,
					status=job.status,
					current_stage=job.current_stage,
					progress_percent=job.progress_percent or 0,
					attempt_number=job.attempt_number,
					error_code=job.error_code,
					error_message=job.error_message,
					queued_at=job.queued_at,
					started_at=job.started_at,
					finished_at=job.finished_at,
				)
				job_events = await events_repo.list_for_job(session, job.id)

		event_payloads = [
			EventPayload(
				id=evt.id,
				event_type=evt.event_type,
				payload_json=evt.payload_json,
				created_at=evt.created_at,
			)
			for evt in job_events
		]

		result = await results_repo.get_by_document_id(session, document_id)
		result_payload = None
		if result:
			result_payload = ResultPayload(
				id=result.id,
				document_id=result.document_id,
				title=result.title,
				category=result.category,
				summary=result.summary,
				keywords=result.keywords_json or [],
				raw_text=result.raw_text,
				structured_json=result.structured_json or {},
				is_finalized=result.is_finalized,
				finalized_at=result.finalized_at,
				version=result.version,
			)

		return DocumentDetailResponse(
			document=doc_payload,
			job=job_payload,
			result=result_payload,
			events=event_payloads,
		)

	except ValueError as exc:
		error_msg = str(exc)
		if "Version mismatch" in error_msg:
			return _error_response(
				code="CONFLICT_VERSION_MISMATCH",
				message=error_msg,
				status_code=409,
			)
		elif "COMPLETED" in error_msg or "status" in error_msg.lower():
			return _error_response(
				code="FINALIZE_NOT_ALLOWED",
				message=error_msg,
				status_code=400,
			)
		else:
			return _error_response(
				code="VALIDATION_ERROR",
				message=error_msg,
				status_code=400,
			)
	except Exception:
		logger.exception("Error finalizing document result")
		return _error_response(
			code="INTERNAL_ERROR",
			message="Failed to finalize document result",
			status_code=500,
		)
