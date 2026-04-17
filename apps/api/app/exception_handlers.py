"""FastAPI exception handlers."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Handle application exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "loc": error["loc"],
                    "msg": error["msg"],
                    "type": error["type"],
                }
            )

        logger.warning(
            f"Validation error on {request.method} {request.url.path}",
            extra={
                "extra_fields": {
                    "errors": errors,
                    "method": request.method,
                    "path": request.url.path,
                }
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "error_code": ErrorCode.INVALID_FILE_EXTENSION.value,  # Generic
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception(
            f"Unhandled exception on {request.method} {request.url.path}",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "exception_type": type(exc).__name__,
                }
            },
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred",
                "error_code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )
