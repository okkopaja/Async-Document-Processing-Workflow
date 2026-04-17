"""Unit tests for constants and enums."""


from app.core.constants import (
    DocumentStatus,
    JobStage,
    STAGE_PROGRESS_MAP,
    ALLOWED_EXTENSIONS,
)


class TestDocumentStatus:
    """Test DocumentStatus enum."""

    def test_document_status_values(self):
        """Test that all document status values are correctly defined."""
        assert DocumentStatus.QUEUED.value == "QUEUED"
        assert DocumentStatus.PROCESSING.value == "PROCESSING"
        assert DocumentStatus.COMPLETED.value == "COMPLETED"
        assert DocumentStatus.FAILED.value == "FAILED"
        assert DocumentStatus.FINALIZED.value == "FINALIZED"

    def test_document_status_count(self):
        """Test that all expected statuses exist."""
        statuses = list(DocumentStatus)
        assert len(statuses) == 5


class TestJobStage:
    """Test JobStage enum."""

    def test_job_stage_values(self):
        """Test that job stages have correct values."""
        assert JobStage.DOCUMENT_RECEIVED.value == "document_received"
        assert JobStage.JOB_QUEUED.value == "job_queued"
        assert JobStage.JOB_STARTED.value == "job_started"
        assert JobStage.DOCUMENT_PARSING_STARTED.value == "document_parsing_started"
        assert JobStage.JOB_COMPLETED.value == "job_completed"

    def test_job_stage_count(self):
        """Test that all expected stages exist."""
        stages = list(JobStage)
        assert len(stages) >= 12  # At least 12 stages


class TestStageProgressMap:
    """Test stage progress mapping."""

    def test_stage_progress_map_exists(self):
        """Test that progress map exists and has values."""
        assert STAGE_PROGRESS_MAP is not None
        assert len(STAGE_PROGRESS_MAP) > 0

    def test_stage_progress_map_values(self):
        """Test that progress values are reasonable."""
        for stage, progress in STAGE_PROGRESS_MAP.items():
            assert isinstance(progress, int)
            assert 0 <= progress <= 100

    def test_job_queued_progress(self):
        """Test that job_queued stage has expected progress."""
        assert STAGE_PROGRESS_MAP[JobStage.JOB_QUEUED.value] == 5

    def test_job_completed_progress(self):
        """Test that job_completed stage has 100% progress."""
        assert STAGE_PROGRESS_MAP[JobStage.JOB_COMPLETED.value] == 100

    def test_progress_monotonic_increase(self):
        """Test that progress generally increases."""
        stages = list(STAGE_PROGRESS_MAP.items())
        for i in range(1, len(stages)):
            # Progress should not decrease significantly
            prev_progress = stages[i - 1][1]
            curr_progress = stages[i][1]
            # Allow some reordering, but generally should increase
            assert curr_progress >= prev_progress - 5


class TestAllowedExtensions:
    """Test allowed file extensions."""

    def test_allowed_extensions_exists(self):
        """Test that allowed extensions set exists."""
        assert ALLOWED_EXTENSIONS is not None
        assert len(ALLOWED_EXTENSIONS) > 0

    def test_allowed_extensions_contains_common_types(self):
        """Test that common file types are allowed."""
        assert "txt" in ALLOWED_EXTENSIONS
        assert "md" in ALLOWED_EXTENSIONS
        assert "pdf" in ALLOWED_EXTENSIONS

    def test_allowed_extensions_are_lowercase(self):
        """Test that all extensions are lowercase."""
        for ext in ALLOWED_EXTENSIONS:
            assert ext == ext.lower()

    def test_no_dots_in_extensions(self):
        """Test that extensions don't include leading dots."""
        for ext in ALLOWED_EXTENSIONS:
            assert not ext.startswith(".")
