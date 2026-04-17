from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.integrations.storage import LocalStorageService, StorageService
from app.services.document_service import DocumentService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
	async for session in get_db():
		yield session


@lru_cache
def _build_storage_service() -> LocalStorageService:
	return LocalStorageService(
		upload_dir=settings.upload_dir,
		max_upload_mb=settings.max_upload_mb,
		allowed_extensions=settings.allowed_extensions,
	)


def get_storage_service() -> StorageService:
	return _build_storage_service()


def get_document_service(
	storage_service: StorageService = Depends(get_storage_service),
) -> DocumentService:
	return DocumentService(storage_service=storage_service)
