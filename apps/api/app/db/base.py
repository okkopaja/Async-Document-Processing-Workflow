from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Alembic autogenerate can discover table metadata.
from app.models import document, document_result, job_event, processing_job  # noqa: E402, F401
