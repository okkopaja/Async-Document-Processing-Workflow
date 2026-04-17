from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExportJsonResponse(BaseModel):
	model_config = ConfigDict(populate_by_name=True)

	document_id: UUID = Field(alias="documentId")
	filename: str
	title: str | None = None
	category: str | None = None
	summary: str | None = None
	keywords: list[str] = Field(default_factory=list)
	status: str
	finalized_at: datetime | None = Field(default=None, alias="finalizedAt")
	structured_json: dict = Field(default_factory=dict, alias="structuredJson")
