"""Integration tests for document processing workflow."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.documents import DocumentsRepository
from app.repositories.jobs import JobsRepository
from app.repositories.results import ResultsRepository
from app.repositories.events import EventsRepository
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.models.document_result import DocumentResult


class TestUploadFlow:
    """Test the upload workflow."""

    @pytest.mark.asyncio
    async def test_document_and_job_creation(
        self,
        test_db: AsyncSession,
        sample_document_data,
        sample_job_data,
    ):
        """Test that document and job are created during upload."""
        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)
        await test_db.flush()

        # Create job
        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        # Verify both were created
        docs_repo = DocumentsRepository()
        jobs_repo = JobsRepository()

        doc_from_db = await docs_repo.get_by_id(test_db, doc.id)
        job_from_db = await jobs_repo.get_by_id(test_db, job.id)

        assert doc_from_db is not None
        assert doc_from_db.status == "QUEUED"
        assert job_from_db is not None
        assert job_from_db.status == "QUEUED"


class TestJobStatusTransitions:
    """Test job status transitions."""

    @pytest.mark.asyncio
    async def test_mark_job_started(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test marking job as started."""

        # Create document and job
        doc = Document(**sample_document_data)
        test_db.add(doc)

        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        # Mark as started
        jobs_repo = JobsRepository()
        updated_job = await jobs_repo.mark_started(test_db, sample_job_id)
        await test_db.flush()

        assert updated_job is not None
        assert updated_job.status == "PROCESSING"
        assert updated_job.current_stage == "job_started"
        assert updated_job.progress_percent == 10
        assert updated_job.started_at is not None

    @pytest.mark.asyncio
    async def test_mark_job_completed(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test marking job as completed."""

        # Create document and job
        doc = Document(**sample_document_data)
        test_db.add(doc)

        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        # Mark as completed
        jobs_repo = JobsRepository()
        updated_job = await jobs_repo.mark_completed(test_db, sample_job_id)
        await test_db.flush()

        assert updated_job is not None
        assert updated_job.status == "COMPLETED"
        assert updated_job.current_stage == "job_completed"
        assert updated_job.progress_percent == 100
        assert updated_job.finished_at is not None

    @pytest.mark.asyncio
    async def test_mark_job_failed(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test marking job as failed."""
        # Create document and job
        doc = Document(**sample_document_data)
        test_db.add(doc)

        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        # Mark as failed
        jobs_repo = JobsRepository()
        updated_job = await jobs_repo.mark_failed(
            test_db, sample_job_id, "PARSE_ERROR", "Failed to parse file"
        )
        await test_db.flush()

        assert updated_job is not None
        assert updated_job.status == "FAILED"
        assert updated_job.current_stage == "job_failed"
        assert updated_job.progress_percent == 100
        assert updated_job.error_code == "PARSE_ERROR"
        assert updated_job.error_message == "Failed to parse file"
        assert updated_job.finished_at is not None


class TestResultPersistence:
    """Test result persistence workflow."""

    @pytest.mark.asyncio
    async def test_create_result(
        self,
        test_db: AsyncSession,
        sample_document_id,
        sample_document_data,
        sample_result_data,
    ):
        """Test creating a document result."""
        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)
        await test_db.flush()

        # Create result
        result = DocumentResult(**sample_result_data)
        test_db.add(result)
        await test_db.flush()

        # Verify result was created
        results_repo = ResultsRepository()
        result_from_db = await results_repo.get_by_document_id(test_db, sample_document_id)

        assert result_from_db is not None
        assert result_from_db.title == "Test Document"
        assert result_from_db.category == "testing"
        assert result_from_db.is_finalized is False

    @pytest.mark.asyncio
    async def test_finalize_result(
        self,
        test_db: AsyncSession,
        sample_document_id,
        sample_document_data,
        sample_result_data,
    ):
        """Test finalizing a result."""
        from datetime import datetime, timezone

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create and finalize result
        sample_result_data["is_finalized"] = True
        sample_result_data["finalized_at"] = datetime.now(timezone.utc)
        result = DocumentResult(**sample_result_data)
        test_db.add(result)
        await test_db.flush()

        # Verify finalization
        results_repo = ResultsRepository()
        result_from_db = await results_repo.get_by_document_id(test_db, sample_document_id)

        assert result_from_db is not None
        assert result_from_db.is_finalized is True
        assert result_from_db.finalized_at is not None
        assert result_from_db.version == 1


class TestEventTracking:
    """Test event tracking workflow."""

    @pytest.mark.asyncio
    async def test_create_event(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test creating job events."""
        from app.models.job_event import JobEvent
        import uuid

        # Create document and job
        doc = Document(**sample_document_data)
        test_db.add(doc)

        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        # Create event
        event = JobEvent(
            id=uuid.uuid4(),
            job_id=sample_job_id,
            event_type="document_received",
            payload_json={"message": "Document received"},
        )
        test_db.add(event)
        await test_db.flush()

        # Verify event was created
        events_repo = EventsRepository()
        events = await events_repo.list_for_job(test_db, sample_job_id)

        assert len(events) == 1
        assert events[0].event_type == "document_received"
        assert events[0].payload_json["message"] == "Document received"

    @pytest.mark.asyncio
    async def test_multiple_events(
        self,
        test_db: AsyncSession,
        sample_job_id,
        sample_document_id,
        sample_document_data,
        sample_job_data,
    ):
        """Test creating multiple events."""
        from app.models.job_event import JobEvent
        import uuid

        # Create document and job
        doc = Document(**sample_document_data)
        test_db.add(doc)

        job = ProcessingJob(**sample_job_data)
        test_db.add(job)
        await test_db.flush()

        # Create multiple events
        event_types = [
            "document_received",
            "parsing_started",
            "parsing_completed",
            "extraction_started",
        ]
        for event_type in event_types:
            event = JobEvent(
                id=uuid.uuid4(),
                job_id=sample_job_id,
                event_type=event_type,
                payload_json={"stage": event_type},
            )
            test_db.add(event)
        await test_db.flush()

        # Verify all events were created
        events_repo = EventsRepository()
        events = await events_repo.list_for_job(test_db, sample_job_id)

        assert len(events) == len(event_types)
        assert all(e.event_type in event_types for e in events)
