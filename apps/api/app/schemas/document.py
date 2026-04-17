from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	document_id: UUID = Field(alias="documentId")
	job_id: UUID = Field(alias="jobId")
	filename: str
	status: str


class DocumentUploadBatchResponse(BaseModel):
	items: list[DocumentUploadResponse]


class DocumentListItem(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	document_id: UUID = Field(alias="documentId")
	original_filename: str = Field(alias="originalFilename")
	mime_type: str = Field(alias="mimeType")
	size_bytes: int = Field(alias="sizeBytes")
	status: str
	created_at: datetime = Field(alias="createdAt")
	latest_job_id: UUID | None = Field(default=None, alias="latestJobId")
	latest_job_status: str | None = Field(default=None, alias="latestJobStatus")
	current_stage: str | None = Field(default=None, alias="currentStage")
	progress_percent: int | None = Field(default=None, alias="progressPercent")
	title: str | None = None
	category: str | None = None
	is_finalized: bool | None = Field(default=None, alias="isFinalized")


class DocumentDetailPayload(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	id: UUID
	original_filename: str = Field(alias="originalFilename")
	mime_type: str = Field(alias="mimeType")
	extension: str
	size_bytes: int = Field(alias="sizeBytes")
	status: str
	created_at: datetime = Field(alias="createdAt")
	updated_at: datetime = Field(alias="updatedAt")
	latest_job_id: UUID | None = Field(default=None, alias="latestJobId")


class JobPayload(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	id: UUID
	status: str
	current_stage: str | None = Field(default=None, alias="currentStage")
	progress_percent: int = Field(alias="progressPercent")
	attempt_number: int = Field(alias="attemptNumber")
	error_code: str | None = Field(default=None, alias="errorCode")
	error_message: str | None = Field(default=None, alias="errorMessage")
	queued_at: datetime = Field(alias="queuedAt")
	started_at: datetime | None = Field(default=None, alias="startedAt")
	finished_at: datetime | None = Field(default=None, alias="finishedAt")


class ResultPayload(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	id: UUID
	document_id: UUID = Field(alias="documentId")
	title: str | None = None
	category: str | None = None
	summary: str | None = None
	keywords: list[str] = Field(default_factory=list)
	raw_text: str | None = Field(default=None, alias="rawText")
	structured_json: dict = Field(default_factory=dict, alias="structuredJson")
	is_finalized: bool = Field(alias="isFinalized")
	finalized_at: datetime | None = Field(default=None, alias="finalizedAt")
	version: int


class EventPayload(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	id: UUID
	event_type: str = Field(alias="eventType")
	payload_json: dict | None = Field(default=None, alias="payload")
	created_at: datetime = Field(alias="createdAt")


class DocumentDetailResponse(BaseModel):
	document: DocumentDetailPayload
	job: JobPayload | None
	result: ResultPayload | None
	events: list[EventPayload]


class DocumentResultUpdate(BaseModel):
	title: str | None = None
	category: str | None = None
	summary: str | None = None
	keywords: list[str] | None = None
	version: int


class FinalizeRequest(BaseModel):
	version: int
