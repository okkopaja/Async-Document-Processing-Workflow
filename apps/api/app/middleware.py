"""Middleware for request logging and correlation tracking."""

import logging
import time
from uuid import uuid4
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import set_correlation_id, set_request_context

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests and responses with correlation tracking."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request, track correlation ID, and log metrics.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        # Generate correlation ID (from header or new)
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        set_correlation_id(correlation_id)

        # Extract context from path parameters
        document_id = request.path_params.get("id") if request.path_params else None
        job_id = request.path_params.get("job_id") if request.path_params else None

        set_request_context(
            request_id=correlation_id,
            document_id=document_id,
            job_id=job_id,
        )

        # Start timing
        start_time = time.time()

        # Call next handler
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log request/response
        log_level = "INFO" if 200 <= response.status_code < 400 else "WARNING"
        logger_func = getattr(logger, log_level.lower())

        logger_func(
            f"{request.method} {request.url.path} - {response.status_code} "
            f"({duration_ms:.1f}ms)",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "correlation_id": correlation_id,
                    "document_id": document_id,
                    "job_id": job_id,
                }
            },
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


class ProcessingMetricsMiddleware(BaseHTTPMiddleware):
    """Track metrics for document processing operations."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track processing metrics."""
        response = await call_next(request)

        # Track upload endpoints
        if request.url.path == "/api/documents/upload" and request.method == "POST":
            logger.info(
                "Document upload completed",
                extra={
                    "extra_fields": {
                        "endpoint": "upload",
                        "status": response.status_code,
                    }
                },
            )

        # Track export endpoints
        elif "/export" in request.url.path and request.method == "GET":
            export_format = "json" if "json" in request.url.path else "csv"
            logger.info(
                f"Document exported as {export_format}",
                extra={
                    "extra_fields": {
                        "endpoint": "export",
                        "format": export_format,
                        "status": response.status_code,
                    }
                },
            )

        return response
