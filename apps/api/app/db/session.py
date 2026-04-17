from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _to_async_database_url(database_url: str) -> str:
	if database_url.startswith("postgresql+psycopg://"):
		return database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
	return database_url


engine = create_async_engine(
	_to_async_database_url(settings.database_url),
	pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
	bind=engine,
	class_=AsyncSession,
	expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
	async with AsyncSessionLocal() as session:
		yield session
