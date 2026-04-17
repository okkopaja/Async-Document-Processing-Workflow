"""Custom exceptions and error handling utilities."""

import logging
from enum import Enum
from typing import Optional, Any, Dict
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes for the API."""

    # File validation errors
    INVALID_FILE_EXTENSION = "INVALID_FILE_EXTENSION"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EMPTY_FILE = "EMPTY_FILE"
    NO_FILES_PROVIDED = "NO_FILES_PROVIDED"

    # Document errors
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    DOCUMENT_ALREADY_EXISTS = "DOCUMENT_ALREADY_EXISTS"

    # Result errors
    RESULT_NOT_FOUND = "RESULT_NOT_FOUND"
    RESULT_FINALIZED = "RESULT_FINALIZED"
    RESULT_NOT_FINALIZED = "RESULT_NOT_FINALIZED"

    # Job errors
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_NOT_RETRYABLE = "JOB_NOT_RETRYABLE"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"

    # Concurrency errors
    VERSION_CONFLICT = "VERSION_CONFLICT"
    OPTIMISTIC_LOCK_FAILED = "OPTIMISTIC_LOCK_FAILED"

    # Processing errors
    PROCESSING_NOT_COMPLETED = "PROCESSING_NOT_COMPLETED"
    PROCESSING_FAILED = "PROCESSING_FAILED"

    # Export errors
    EXPORT_NOT_ALLOWED = "EXPORT_NOT_ALLOWED"
    EXPORT_FAILED = "EXPORT_FAILED"

    # System errors
    DATABASE_ERROR = "DATABASE_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        error_code: ErrorCode,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize app exception.

        Args:
            error_code: Standardized error code
            detail: User-friendly error message
            status_code: HTTP status code
            context: Additional context for logging
        """
        self.error_code = error_code
        self.detail = detail
        self.status_code = status_code
        self.context = context or {}

        # Log error with context
        logger.warning(
            f"AppException: {error_code.value} - {detail}",
            extra={
                "extra_fields": {
                    "error_code": error_code.value,
                    "status_code": status_code,
                    **self.context,
                }
            },
        )

        super().__init__(detail)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to JSON-serializable dict."""
        return {
            "detail": self.detail,
            "error_code": self.error_code.value,
            "status_code": self.status_code,
        }

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict(),
        )


class ValidationError(AppException):
    """Validation error (400 Bad Request)."""

    def __init__(self, detail: str, error_code: ErrorCode, context: Optional[Dict] = None):
        super().__init__(
            error_code=error_code,
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            context=context,
        )


class NotFoundError(AppException):
    """Resource not found (404 Not Found)."""

    def __init__(self, detail: str, error_code: ErrorCode, context: Optional[Dict] = None):
        super().__init__(
            error_code=error_code,
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )


class ConflictError(AppException):
    """Conflict error (409 Conflict)."""

    def __init__(self, detail: str, error_code: ErrorCode, context: Optional[Dict] = None):
        super().__init__(
            error_code=error_code,
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
            context=context,
        )


# Specific exception classes

class InvalidFileExtensionError(ValidationError):
    """File has invalid extension."""

    def __init__(self, extension: str, allowed: list[str]):
        detail = f"Invalid file extension: .{extension} (allowed: {', '.join(allowed)})"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.INVALID_FILE_EXTENSION,
            context={"extension": extension, "allowed": allowed},
        )


class FileTooLargeError(ValidationError):
    """File exceeds maximum size."""

    def __init__(self, size_mb: float, max_mb: int):
        detail = f"File size {size_mb:.1f} MB exceeds maximum {max_mb} MB"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.FILE_TOO_LARGE,
            context={"size_mb": size_mb, "max_mb": max_mb},
        )


class EmptyFileError(ValidationError):
    """File is empty."""

    def __init__(self, filename: str):
        detail = f"File '{filename}' is empty"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.EMPTY_FILE,
            context={"filename": filename},
        )


class DocumentNotFoundError(NotFoundError):
    """Document not found."""

    def __init__(self, document_id: str):
        detail = "Document not found"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.DOCUMENT_NOT_FOUND,
            context={"document_id": document_id},
        )


class ResultNotFoundError(NotFoundError):
    """Result not found."""

    def __init__(self, document_id: str):
        detail = "Document result not found"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.RESULT_NOT_FOUND,
            context={"document_id": document_id},
        )


class ResultFinalizedError(ValidationError):
    """Cannot edit finalized result."""

    def __init__(self, result_id: str):
        detail = "Result is finalized and cannot be edited"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.RESULT_FINALIZED,
            context={"result_id": result_id},
        )


class VersionConflictError(ConflictError):
    """Optimistic lock failure - version mismatch."""

    def __init__(self, expected_version: int, provided_version: int):
        detail = (
            f"Version mismatch: expected {expected_version}, "
            f"got {provided_version} (result was updated)"
        )
        super().__init__(
            detail=detail,
            error_code=ErrorCode.VERSION_CONFLICT,
            context={
                "expected_version": expected_version,
                "provided_version": provided_version,
            },
        )


class JobNotFoundError(NotFoundError):
    """Job not found."""

    def __init__(self, job_id: str):
        detail = "Job not found"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.JOB_NOT_FOUND,
            context={"job_id": job_id},
        )


class JobNotRetryableError(ValidationError):
    """Job cannot be retried (must be FAILED status)."""

    def __init__(self, job_id: str, current_status: str):
        detail = f"Only FAILED jobs can be retried (current status: {current_status})"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.JOB_NOT_RETRYABLE,
            context={"job_id": job_id, "current_status": current_status},
        )


class ProcessingNotCompletedError(ValidationError):
    """Document processing not yet completed."""

    def __init__(self, document_id: str, status: str):
        detail = f"Document processing not completed yet (status: {status})"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.PROCESSING_NOT_COMPLETED,
            context={"document_id": document_id, "status": status},
        )


class ExportNotAllowedError(ValidationError):
    """Cannot export non-finalized result."""

    def __init__(self, document_id: str, reason: str = "not finalized"):
        detail = f"Document is {reason}, export not allowed"
        super().__init__(
            detail=detail,
            error_code=ErrorCode.EXPORT_NOT_ALLOWED,
            context={"document_id": document_id, "reason": reason},
        )


class DatabaseError(AppException):
    """Database operation failed."""

    def __init__(self, operation: str, details: str):
        detail = f"Database error during {operation}"
        super().__init__(
            error_code=ErrorCode.DATABASE_ERROR,
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            context={"operation": operation, "details": details},
        )
        # Log full error for debugging
        logger.error(f"DatabaseError in {operation}: {details}")


class StorageError(AppException):
    """File storage operation failed."""

    def __init__(self, operation: str, filename: str):
        detail = f"Failed to {operation} file '{filename}'"
        super().__init__(
            error_code=ErrorCode.STORAGE_ERROR,
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            context={"operation": operation, "filename": filename},
        )
        # Log full error for debugging
        logger.error(f"StorageError during {operation}: {filename}")


# Service layer exception classes

class ServiceException(AppException):
    """Service layer exception."""

    pass


class DocumentServiceError(ServiceException):
    """Error in DocumentService."""

    pass


class ResultServiceError(ServiceException):
    """Error in ResultService."""

    pass


class JobServiceError(ServiceException):
    """Error in JobService."""

    pass


class ExportServiceError(ServiceException):
    """Error in ExportService."""

    pass


def handle_exception(exc: Exception) -> HTTPException:
    """
    Convert application exception to HTTP exception.

    Args:
        exc: Exception to handle

    Returns:
        HTTPException for FastAPI
    """
    if isinstance(exc, AppException):
        return exc.to_http_exception()

    # Unknown error
    logger.exception("Unhandled exception")
    error = AppException(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return error.to_http_exception()
