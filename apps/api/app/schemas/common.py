from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
	page: int = Field(default=1, ge=1)
	page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
	model_config = ConfigDict(populate_by_name=True)

	items: list[T]
	page: int
	page_size: int = Field(alias="pageSize")
	total: int


class ErrorDetail(BaseModel):
	code: str
	message: str


class ErrorResponse(BaseModel):
	error: ErrorDetail
