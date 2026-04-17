from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobDetail(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	job_id: UUID = Field(alias="jobId")
	document_id: UUID = Field(alias="documentId")
	status: str
	current_stage: str | None = Field(default=None, alias="currentStage")
	progress_percent: int = Field(alias="progressPercent")
	attempt_number: int = Field(alias="attemptNumber")
	queued_at: datetime = Field(alias="queuedAt")
	started_at: datetime | None = Field(default=None, alias="startedAt")
	finished_at: datetime | None = Field(default=None, alias="finishedAt")
	error_code: str | None = Field(default=None, alias="errorCode")
	error_message: str | None = Field(default=None, alias="errorMessage")


class RetryResponse(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	job_id: UUID = Field(alias="jobId")
	document_id: UUID = Field(alias="documentId")
	status: str
