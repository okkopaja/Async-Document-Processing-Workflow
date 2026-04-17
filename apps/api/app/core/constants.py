from enum import StrEnum


class DocumentStatus(StrEnum):
	QUEUED = "QUEUED"
	PROCESSING = "PROCESSING"
	COMPLETED = "COMPLETED"
	FAILED = "FAILED"
	FINALIZED = "FINALIZED"


class JobStage(StrEnum):
	DOCUMENT_RECEIVED = "document_received"
	JOB_QUEUED = "job_queued"
	JOB_STARTED = "job_started"
	DOCUMENT_PARSING_STARTED = "document_parsing_started"
	DOCUMENT_PARSING_COMPLETED = "document_parsing_completed"
	FIELD_EXTRACTION_STARTED = "field_extraction_started"
	FIELD_EXTRACTION_COMPLETED = "field_extraction_completed"
	RESULT_PERSIST_STARTED = "result_persist_started"
	RESULT_PERSIST_COMPLETED = "result_persist_completed"
	JOB_COMPLETED = "job_completed"
	JOB_FAILED = "job_failed"
	JOB_RETRY_SCHEDULED = "job_retry_scheduled"


STAGE_PROGRESS_MAP: dict[str, int] = {
	JobStage.JOB_QUEUED.value: 5,
	JobStage.JOB_STARTED.value: 10,
	JobStage.DOCUMENT_PARSING_STARTED.value: 20,
	JobStage.DOCUMENT_PARSING_COMPLETED.value: 40,
	JobStage.FIELD_EXTRACTION_STARTED.value: 55,
	JobStage.FIELD_EXTRACTION_COMPLETED.value: 75,
	JobStage.RESULT_PERSIST_STARTED.value: 85,
	JobStage.RESULT_PERSIST_COMPLETED.value: 95,
	JobStage.JOB_COMPLETED.value: 100,
}


ALLOWED_EXTENSIONS: set[str] = {"txt", "md", "pdf", "docx", "csv"}


class TransientParseError(Exception):
	"""Retryable parsing error."""
	pass


class PermanentParseError(Exception):
	"""Non-retryable parsing error."""
	pass


class UnsupportedFileTypeError(Exception):
	"""File type not supported."""
	pass
