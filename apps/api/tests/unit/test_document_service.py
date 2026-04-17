"""Unit tests for document service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.storage import LocalStorageService
from app.models.document import Document
from app.models.document_result import DocumentResult
from app.models.job_event import JobEvent
from app.models.processing_job import ProcessingJob
from app.services.document_service import DocumentDeleteError, DocumentService


class TestDocumentServiceDelete:
    """Test DocumentService delete_document method."""

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, test_db: AsyncSession, tmp_path):
        """Deleting a missing document raises a 404-style service error."""
        service = DocumentService(
            storage_service=LocalStorageService(
                upload_dir=str(tmp_path),
                max_upload_mb=25,
                allowed_extensions=["txt"],
            ),
            task_client=Mock(),
        )

        with pytest.raises(DocumentDeleteError) as exc_info:
            await service.delete_document(test_db, uuid.uuid4())

        assert exc_info.value.code == "DOCUMENT_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document_removes_related_rows_and_storage(
        self,
        test_db: AsyncSession,
        tmp_path,
    ):
        """Delete removes document metadata, dependent rows, and upload artifacts."""
        document_id = uuid.uuid4()
        job_id = uuid.uuid4()
        result_id = uuid.uuid4()
        event_id = uuid.uuid4()

        document_dir = tmp_path / str(document_id)
        document_dir.mkdir(parents=True, exist_ok=True)
        storage_path = document_dir / "payload.txt"
        storage_path.write_text("sample", encoding="utf-8")

        document = Document(
            id=document_id,
            original_filename="payload.txt",
            stored_filename="stored_payload.txt",
            mime_type="text/plain",
            extension="txt",
            size_bytes=6,
            storage_path=str(storage_path),
            status="PROCESSING",
        )
        test_db.add(document)
        await test_db.flush()

        job = ProcessingJob(
            id=job_id,
            document_id=document_id,
            celery_task_id="task-abc",
            status="PROCESSING",
            current_stage="job_started",
            progress_percent=25,
            attempt_number=1,
            queued_at=datetime.now(timezone.utc),
        )
        test_db.add(job)
        await test_db.flush()

        document.latest_job_id = job_id

        result = DocumentResult(
            id=result_id,
            document_id=document_id,
            title="title",
            category="category",
            summary="summary",
            keywords_json=["one"],
            raw_text="raw",
            structured_json={"k": "v"},
            is_finalized=False,
            version=1,
        )
        test_db.add(result)

        event = JobEvent(
            id=event_id,
            job_id=job_id,
            event_type="job_started",
            payload_json={"status": "PROCESSING"},
        )
        test_db.add(event)

        await test_db.commit()

        mock_control = Mock()
        mock_task_client = Mock()
        mock_task_client.control = mock_control

        service = DocumentService(
            storage_service=LocalStorageService(
                upload_dir=str(tmp_path),
                max_upload_mb=25,
                allowed_extensions=["txt"],
            ),
            task_client=mock_task_client,
        )

        await service.delete_document(test_db, document_id)

        assert await test_db.get(Document, document_id) is None

        job_count = await test_db.scalar(
            sa.select(sa.func.count()).select_from(ProcessingJob).where(ProcessingJob.document_id == document_id)
        )
        assert job_count == 0

        result_count = await test_db.scalar(
            sa.select(sa.func.count()).select_from(DocumentResult).where(DocumentResult.document_id == document_id)
        )
        assert result_count == 0

        event_count = await test_db.scalar(sa.select(sa.func.count()).select_from(JobEvent))
        assert event_count == 0

        assert not storage_path.exists()
        assert not document_dir.exists()

        mock_control.revoke.assert_called_once_with("task-abc", terminate=True)