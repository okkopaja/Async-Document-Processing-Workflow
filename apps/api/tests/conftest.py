"""Test configuration and fixtures."""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.repositories.documents import DocumentsRepository
from app.repositories.jobs import JobsRepository
from app.repositories.results import ResultsRepository
from app.repositories.events import EventsRepository


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory SQLite test database."""
    # Use in-memory SQLite for fast tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_sessionmaker_instance = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_sessionmaker_instance() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def sample_document_id() -> uuid.UUID:
    """Generate a sample document ID."""
    return uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def sample_job_id() -> uuid.UUID:
    """Generate a sample job ID."""
    return uuid.UUID("660e8400-e29b-41d4-a716-446655440000")


@pytest.fixture
def sample_document_data(sample_document_id: uuid.UUID) -> dict:
    """Create sample document data."""
    return {
        "id": sample_document_id,
        "original_filename": "test-document.txt",
        "stored_filename": f"{sample_document_id}_test-document.txt",
        "mime_type": "text/plain",
        "extension": "txt",
        "size_bytes": 1024,
        "storage_path": f"/uploads/{sample_document_id}/test-document.txt",
        "status": "QUEUED",
    }


@pytest.fixture
def sample_job_data(sample_job_id: uuid.UUID, sample_document_id: uuid.UUID) -> dict:
    """Create sample job data."""
    return {
        "id": sample_job_id,
        "document_id": sample_document_id,
        "celery_task_id": "task-123",
        "status": "QUEUED",
        "current_stage": "job_queued",
        "progress_percent": 5,
        "attempt_number": 1,
        "queued_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_result_data(sample_document_id: uuid.UUID) -> dict:
    """Create sample result data."""
    return {
        "document_id": sample_document_id,
        "title": "Test Document",
        "category": "testing",
        "summary": "This is a test document summary.",
        "keywords_json": ["test", "document", "sample"],
        "raw_text": "This is test content.",
        "structured_json": {"type": "test", "content": "sample"},
        "is_finalized": False,
        "version": 1,
    }


@pytest.fixture
async def documents_repository(test_db: AsyncSession) -> DocumentsRepository:
    """Create a documents repository with test database."""
    repo = DocumentsRepository()
    return repo


@pytest.fixture
async def jobs_repository(test_db: AsyncSession) -> JobsRepository:
    """Create a jobs repository with test database."""
    repo = JobsRepository()
    return repo


@pytest.fixture
async def results_repository(test_db: AsyncSession) -> ResultsRepository:
    """Create a results repository with test database."""
    repo = ResultsRepository()
    return repo


@pytest.fixture
async def events_repository(test_db: AsyncSession) -> EventsRepository:
    """Create an events repository with test database."""
    repo = EventsRepository()
    return repo
