import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.services.export_service import ExportService, ExportServiceError

logger = logging.getLogger(__name__)
router = APIRouter()


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
	return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def get_export_service() -> ExportService:
	return ExportService()


@router.get(
	"/documents/{document_id}/export.json",
	status_code=status.HTTP_200_OK,
)
async def export_json(
	document_id: Annotated[uuid.UUID, Path()],
	session: Annotated[AsyncSession, Depends(get_db_session)],
	export_service: Annotated[ExportService, Depends(get_export_service)],
) -> dict[str, object]:
	"""
	Export a finalized document result as JSON.

	Per design doc §8.2.2:
	- Returns JSON file with Content-Disposition: attachment
	- Only available for finalized results
	- Returns EXPORT_NOT_ALLOWED (400) if not finalized
	- Returns DOCUMENT_NOT_FOUND (404) if document not found
	"""
	try:
		result = await export_service.export_json(session, document_id)
		return result
	except ExportServiceError as exc:
		return _error_response(code=exc.code, message=exc.message, status_code=exc.status_code)
	except Exception as exc:
		logger.error(f"Error exporting document {document_id} as JSON: {exc}")
		return _error_response(
			code="INTERNAL_ERROR",
			message="An error occurred while exporting the document",
			status_code=500,
		)


@router.get(
	"/documents/{document_id}/export.csv",
	status_code=status.HTTP_200_OK,
)
async def export_csv(
	document_id: Annotated[uuid.UUID, Path()],
	session: Annotated[AsyncSession, Depends(get_db_session)],
	export_service: Annotated[ExportService, Depends(get_export_service)],
) -> dict[str, object]:
	"""
	Export a finalized document result as CSV.

	Per design doc §8.2.3:
	- Returns CSV file with Content-Type: text/csv and attachment disposition
	- Only available for finalized results
	- Returns EXPORT_NOT_ALLOWED (400) if not finalized
	- Returns DOCUMENT_NOT_FOUND (404) if document not found
	"""
	try:
		csv_content = await export_service.export_csv(session, document_id)
		return {
			"csv_data": csv_content,
		}
	except ExportServiceError as exc:
		return _error_response(code=exc.code, message=exc.message, status_code=exc.status_code)
	except Exception as exc:
		logger.error(f"Error exporting document {document_id} as CSV: {exc}")
		return _error_response(
			code="INTERNAL_ERROR",
			message="An error occurred while exporting the document",
			status_code=500,
		)
