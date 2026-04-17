from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProgressEvent(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	event_id: UUID = Field(alias="eventId")
	job_id: UUID = Field(alias="jobId")
	document_id: UUID = Field(alias="documentId")
	status: str
	stage: str
	progress_percent: int = Field(alias="progressPercent")
	message: str
	attempt_number: int = Field(alias="attemptNumber")
	timestamp: datetime
