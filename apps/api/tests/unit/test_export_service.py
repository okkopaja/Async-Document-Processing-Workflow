"""Unit tests for export service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.export_service import ExportService, ExportServiceError


class TestExportService:
    """Test ExportService export methods."""

    @pytest.mark.asyncio
    async def test_export_json_missing_document(self, test_db: AsyncSession):
        """Test export_json with non-existent document."""
        service = ExportService()
        import uuid

        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        with pytest.raises(ExportServiceError) as exc_info:
            await service.export_json(test_db, non_existent_id)

        assert exc_info.value.code == "DOCUMENT_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_csv_missing_document(self, test_db: AsyncSession):
        """Test export_csv with non-existent document."""
        service = ExportService()
        import uuid

        non_existent_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

        with pytest.raises(ExportServiceError) as exc_info:
            await service.export_csv(test_db, non_existent_id)

        assert exc_info.value.code == "DOCUMENT_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_json_not_finalized(
        self,
        test_db: AsyncSession,
        sample_document_id,
        sample_document_data,
        sample_result_data,
    ):
        """Test export_json fails if result not finalized."""
        from app.models.document import Document
        from app.models.document_result import DocumentResult

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create non-finalized result
        sample_result_data["is_finalized"] = False
        result = DocumentResult(**sample_result_data)
        test_db.add(result)
        await test_db.flush()

        service = ExportService()

        with pytest.raises(ExportServiceError) as exc_info:
            await service.export_json(test_db, sample_document_id)

        assert exc_info.value.code == "EXPORT_NOT_ALLOWED"
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_export_csv_not_finalized(
        self,
        test_db: AsyncSession,
        sample_document_id,
        sample_document_data,
        sample_result_data,
    ):
        """Test export_csv fails if result not finalized."""
        from app.models.document import Document
        from app.models.document_result import DocumentResult

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create non-finalized result
        sample_result_data["is_finalized"] = False
        result = DocumentResult(**sample_result_data)
        test_db.add(result)
        await test_db.flush()

        service = ExportService()

        with pytest.raises(ExportServiceError) as exc_info:
            await service.export_csv(test_db, sample_document_id)

        assert exc_info.value.code == "EXPORT_NOT_ALLOWED"
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_export_json_finalized(
        self,
        test_db: AsyncSession,
        sample_document_id,
        sample_document_data,
        sample_result_data,
    ):
        """Test export_json with finalized result."""
        from app.models.document import Document
        from app.models.document_result import DocumentResult
        from datetime import datetime, timezone

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create finalized result
        sample_result_data["is_finalized"] = True
        sample_result_data["finalized_at"] = datetime.now(timezone.utc)
        result = DocumentResult(**sample_result_data)
        test_db.add(result)
        await test_db.flush()

        service = ExportService()
        export_data = await service.export_json(test_db, sample_document_id)

        # Verify structure
        assert export_data["documentId"] == str(sample_document_id)
        assert export_data["filename"] == "test-document.txt"
        assert export_data["title"] == "Test Document"
        assert export_data["category"] == "testing"
        assert export_data["status"] == "QUEUED"
        assert export_data["keywords"] == ["test", "document", "sample"]
        assert export_data["finalizedAt"] is not None

    @pytest.mark.asyncio
    async def test_export_csv_finalized(
        self,
        test_db: AsyncSession,
        sample_document_id,
        sample_document_data,
        sample_result_data,
    ):
        """Test export_csv with finalized result."""
        from app.models.document import Document
        from app.models.document_result import DocumentResult
        from datetime import datetime, timezone

        # Create document
        doc = Document(**sample_document_data)
        test_db.add(doc)

        # Create finalized result
        sample_result_data["is_finalized"] = True
        sample_result_data["finalized_at"] = datetime.now(timezone.utc)
        result = DocumentResult(**sample_result_data)
        test_db.add(result)
        await test_db.flush()

        service = ExportService()
        csv_content = await service.export_csv(test_db, sample_document_id)

        # Verify CSV structure
        assert "document_id" in csv_content
        assert "filename" in csv_content
        assert "title" in csv_content
        assert "category" in csv_content
        assert "test-document.txt" in csv_content
        assert "Test Document" in csv_content
        assert "testing" in csv_content
