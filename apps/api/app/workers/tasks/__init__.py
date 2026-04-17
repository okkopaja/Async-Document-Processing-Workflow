"""Celery task package exports."""

from app.workers.tasks.process_document import process_document

__all__ = ["process_document"]

