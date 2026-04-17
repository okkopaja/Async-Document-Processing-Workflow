"""Unit tests for job service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_service import JobService, JobServiceError


class TestJobServiceRetry:
    """Test JobService retry_failed_job method."""

    @pytest.mark.asyncio
    async def test_retry_job_not_found(self, test_db: AsyncSession):
        """Test retry_failed_job with non-existent job."""
        service = JobService()
        import uuid

        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        with pytest.raises(JobServiceError) as exc_info:
            await service.retry_failed_job(test_db, non_existent_id)

        assert exc_info.value.code == "JOB_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_job_not_retryable(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test retry_failed_job with non-failed job."""
        from app.models.document import Document
        from app.models.processing_job import ProcessingJob

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create job with QUEUED status (not FAILED)
        sample_job_data["status"] = "QUEUED"
        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        service = JobService()

        with pytest.raises(JobServiceError) as exc_info:
            await service.retry_failed_job(test_db, sample_job_id)

        assert exc_info.value.code == "JOB_NOT_RETRYABLE"
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_failed_job_success(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test retry_failed_job successfully creates new job."""
        from app.models.document import Document
        from app.models.processing_job import ProcessingJob
        from app.repositories.jobs import JobsRepository

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create failed job
        sample_job_data["status"] = "FAILED"
        sample_job_data["attempt_number"] = 1
        sample_job_data["error_code"] = "PARSE_ERROR"
        sample_job_data["error_message"] = "Failed to parse file"
        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        service = JobService(jobs_repo=JobsRepository())
        result = await service.retry_failed_job(test_db, sample_job_id)

        # Verify result
        assert "jobId" in result
        assert "documentId" in result
        assert result["documentId"] == str(sample_document_id)
        assert result["attemptNumber"] == 2

    @pytest.mark.asyncio
    async def test_retry_increments_attempt_number(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test that retry increments attempt number."""
        from app.models.document import Document
        from app.models.processing_job import ProcessingJob
        from app.repositories.jobs import JobsRepository

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create failed job with attempt_number = 2
        sample_job_data["status"] = "FAILED"
        sample_job_data["attempt_number"] = 2
        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        service = JobService(jobs_repo=JobsRepository())
        result = await service.retry_failed_job(test_db, sample_job_id)

        # Verify attempt number incremented
        assert result["attemptNumber"] == 3

    @pytest.mark.asyncio
    async def test_retry_creates_queued_job(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test that retry creates job with QUEUED status."""
        from app.models.document import Document
        from app.models.processing_job import ProcessingJob
        from app.repositories.jobs import JobsRepository
        import uuid

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create failed job
        sample_job_data["status"] = "FAILED"
        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        service = JobService(jobs_repo=JobsRepository())
        result = await service.retry_failed_job(test_db, sample_job_id)

        # Fetch newly created job
        jobs_repo = JobsRepository()
        new_job_id = uuid.UUID(result["jobId"])
        new_job = await jobs_repo.get_by_id(test_db, new_job_id)

        assert new_job is not None
        assert new_job.status == "QUEUED"
        assert new_job.attempt_number == 2
