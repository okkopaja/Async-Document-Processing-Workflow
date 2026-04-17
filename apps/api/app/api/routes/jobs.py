import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.services.job_service import JobService, JobServiceError

logger = logging.getLogger(__name__)
router = APIRouter()


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
	return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def get_job_service() -> JobService:
	return JobService()


@router.post(
	"/{job_id}/retry",
	status_code=status.HTTP_202_ACCEPTED,
)
async def retry_job(
	job_id: Annotated[uuid.UUID, Path()],
	session: Annotated[AsyncSession, Depends(get_db_session)],
	job_service: Annotated[JobService, Depends(get_job_service)],
) -> dict[str, object]:
	"""
	Retry a failed job.

	Per design doc §8.1.2:
	- Validates job exists and is in FAILED status
	- Creates new job with incremented attempt number
	- Updates document status to QUEUED
	- Dispatches new Celery task
	- Returns 202 Accepted with new jobId and documentId
	"""
	try:
		result = await job_service.retry_failed_job(session, job_id)
		await session.commit()
		return result
	except JobServiceError as exc:
		return _error_response(code=exc.code, message=exc.message, status_code=exc.status_code)
	except Exception as exc:
		logger.error(f"Error retrying job {job_id}: {exc}")
		return _error_response(
			code="INTERNAL_ERROR",
			message="An error occurred while retrying the job",
			status_code=500,
		)
