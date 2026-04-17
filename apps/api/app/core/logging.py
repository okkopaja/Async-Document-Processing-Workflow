"""Structured logging configuration with correlation tracking."""

import logging
import json
import uuid
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime, timezone

# Context variable for correlation IDs (request tracing)
_correlation_id: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "request_context", default=None
)


class CorrelationFilter(logging.Filter):
    """Add correlation ID to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID and request context to log record."""
        correlation_id = get_correlation_id()
        record.correlation_id = correlation_id or "none"

        request_context = get_request_context()
        if request_context:
            record.request_id = request_context.get("request_id", "none")
            record.user_id = request_context.get("user_id", "none")
            record.document_id = request_context.get("document_id", "none")
            record.job_id = request_context.get("job_id", "none")
        else:
            record.request_id = "none"
            record.user_id = "none"
            record.document_id = "none"
            record.job_id = "none"

        return True


class StructuredFormatter(logging.Formatter):
    """Format logs as structured JSON for easy parsing."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with context information."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "none"),
            "request_id": getattr(record, "request_id", "none"),
        }

        # Add extra fields from record
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra context
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class SimpleFormatter(logging.Formatter):
    """Simple text format with correlation ID (for console)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with correlation ID."""
        correlation_id = getattr(record, "correlation_id", "none")[:8]
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        return (
            f"{timestamp} | {record.levelname:8} | "
            f"[{correlation_id}] | "
            f"{record.name:30} | {record.getMessage()}"
        )


def configure_logging(
    level: str = "INFO", json_format: bool = False, log_file: Optional[str] = None
) -> None:
    """
    Configure structured logging with correlation tracking.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, output JSON format; else human-readable
        log_file: Optional file path to write logs
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Add correlation filter to all handlers
    correlation_filter = CorrelationFilter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.addFilter(correlation_filter)

    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = SimpleFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.addFilter(correlation_filter)
        file_handler.setFormatter(StructuredFormatter())  # Always JSON for files
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for request tracing.

    Args:
        correlation_id: Custom correlation ID; if None, generates UUID

    Returns:
        The correlation ID (either provided or generated)
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    _correlation_id.set(correlation_id)
    return correlation_id


def get_request_context() -> Optional[Dict[str, Any]]:
    """Get current request context."""
    return _request_context.get()


def set_request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    document_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Set request context for tracking.

    Args:
        request_id: HTTP request ID
        user_id: User ID if authenticated
        document_id: Document being processed
        job_id: Job being processed

    Returns:
        The context dictionary
    """
    context = {
        "request_id": request_id or str(uuid.uuid4()),
        "user_id": user_id,
        "document_id": document_id,
        "job_id": job_id,
    }
    _request_context.set(context)
    return context


def get_logger(name: str) -> logging.LoggerAdapter:
    """
    Get a structured logger with convenience methods.

    Args:
        name: Logger name (typically __name__)

    Returns:
        LoggerAdapter with extra context
    """
    base_logger = logging.getLogger(name)

    def log_with_context(msg: str, **kwargs):
        extra = {"extra_fields": kwargs}
        base_logger.info(msg, extra=extra)

    return base_logger
