from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, exports, jobs, ws_progress
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware import RequestLoggingMiddleware, ProcessingMetricsMiddleware
from app.exception_handlers import register_exception_handlers


# Configure structured logging
configure_logging(
    level=settings.log_level,
    json_format=False,  # Console is readable; set to True for production
)


def create_app() -> FastAPI:
    app = FastAPI(title="DocFlow API", version="1.0.0")

    # Register exception handlers
    register_exception_handlers(app)

    # Add middleware in reverse order (last one added is first one executed)
    app.add_middleware(ProcessingMetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(exports.router, prefix="/api/exports", tags=["exports"])
    app.include_router(ws_progress.router, tags=["websockets"])

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
