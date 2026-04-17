# Async Document Processing Workflow

Asynchronous document processing system built with Next.js, FastAPI, Celery, Redis, and PostgreSQL.

## What This Project Does

This project lets users:

1. Upload one or more supported files from a web UI.
2. Queue processing jobs asynchronously.
3. Track stage-by-stage progress in real time.
4. Review and edit extracted fields.
5. Finalize reviewed results.
6. Export finalized results as JSON or CSV.
7. Retry failed jobs while preserving attempt history.

Supported file extensions: txt, md, pdf, docx, csv.

## How It Works

1. Frontend sends file uploads to the API.
2. API validates files, stores them, writes document and job rows to PostgreSQL, and dispatches a Celery task.
3. Worker executes parse, extract, and persist pipeline stages.
4. Worker writes state changes to PostgreSQL first, then publishes transient progress events to Redis Pub/Sub.
5. API WebSocket endpoints relay Redis events to browser clients.
6. Frontend updates progress UI from WebSocket and uses REST as recovery source of truth.

Core architectural rules implemented in the plan:

- No synchronous document processing in HTTP handlers.
- PostgreSQL is the durable source of truth.
- Redis Pub/Sub is for live notifications only.
- Frontend correctness depends on REST refetch, not only WebSocket delivery.

## Tech Stack

- Frontend: Next.js (App Router), React, TypeScript, TanStack Query
- API: FastAPI, Pydantic v2, SQLAlchemy, Alembic
- Worker: Celery
- Data and messaging: PostgreSQL, Redis Pub/Sub
- Monorepo: pnpm workspace, Turborepo
- Local orchestration: Docker Compose

## Project Structure

- apps/
  - api/
    - app/
      - api/routes/ (documents, jobs, exports, websockets)
      - core/ (config, constants, celery app, logging)
      - db/ (session, base, migrations)
      - models/ (documents, processing jobs, results, events)
      - repositories/ (data access)
      - schemas/ (request and response models)
      - services/ (upload, review, retry, export)
      - integrations/ (storage, redis, parsers)
      - workers/ (tasks and pipelines)
    - tests/ (unit and integration)
  - web/
    - app/ (dashboard, upload, document detail pages)
    - components/ (dashboard, documents, forms, ui)
    - hooks/ (job and document progress)
    - lib/ (API and WebSocket clients)
    - types/
- packages/shared-types/
- infra/
  - compose/
  - docker/
  - scripts/
- docs/
  - architecture.md
  - api-contracts.md
  - demo-script.md
  - decisions/
- sample-files/
- sample-exports/

## Setup

### Prerequisites

- Docker Desktop with Compose v2
- Node.js 20+
- pnpm 9+
- Python 3.12+
- uv

### Option A: Run with Docker Compose (Recommended)

From repo root:

1. Copy environment template if you want a writable local env file.
   - cp .env.example .env
2. Start services:
   - docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.example up --build
3. Access:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Health: http://localhost:8000/api/health
   - Flower: http://localhost:5555
4. Stop:
   - docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.example down -v

Note: helper scripts in infra/scripts are bash scripts.

### Option B: Run Locally Without Docker

Backend terminal:

1. cd apps/api
2. uv venv
3. Activate env
   - PowerShell: .venv\Scripts\Activate.ps1
4. uv sync
5. uv run alembic upgrade head
6. uv run uvicorn app.main:app --reload --port 8000

Worker terminal:

1. cd apps/api
2. uv run celery -A app.core.celery_app.celery_app worker --loglevel=info

Frontend terminal:

1. cd apps/web
2. pnpm install
3. pnpm dev

## API Surface

- POST /api/documents/upload
- GET /api/documents
- GET /api/documents/{document_id}
- PATCH /api/documents/{document_id}/result
- POST /api/documents/{document_id}/finalize
- POST /api/jobs/{job_id}/retry
- GET /api/exports/documents/{document_id}/export.json
- GET /api/exports/documents/{document_id}/export.csv
- WS /ws/jobs/{job_id}
- WS /ws/documents/{document_id}
- GET /api/health

## Audit Snapshot (2026-04-16)

Implementation plan checklist and executable checks were audited against this repository.

### Checklist Coverage

- Appendix A file checklist: 85/88 present.
- Missing plan-named files:
  - docs/decisions/001-monorepo.md
  - docs/decisions/002-websockets-over-sse.md
  - docs/decisions/003-postgres-authoritative-state.md

Equivalent ADRs currently present:

- docs/decisions/001-postgresql-authoritative.md
- docs/decisions/002-async-processing.md
- docs/decisions/003-optimistic-concurrency.md

### Sanity Check Results

Backend checks executed:

- uv run pytest -q
- uv run ruff check app tests

Observed:

- Tests: 13 passed, 19 errors.
- Primary blocking error: missing test dependency aiosqlite.
- Ruff: 40 violations (unused imports/variables, duplicate exception class, etc.).

Frontend checks executed:

- pnpm --filter web lint
- pnpm --filter web build

Observed:

- Lint: 4 errors, 9 warnings.
- Build: fails type-check because DocumentDetailResponse is imported in app/documents/[documentId]/page.tsx but not exported from apps/web/types/index.ts.

### Functional Alignment Notes

The architecture and major modules are mostly present, but current health checks do not pass. Based on this audit, the codebase is close to plan-level structural completion but is not yet in a fully working or release-ready state.

## Documentation

- docs/architecture.md
- docs/api-contracts.md
- docs/demo-script.md
- docs/implementation plans/Implementation_Plan_v1.0.md
- docs/design docs/Design_Doc_1.0.md

## Known Gaps to Resolve Next

1. Add missing dev dependency for async SQLite tests or adjust test DB strategy.
2. Fix backend lint violations.
3. Fix frontend lint violations.
4. Add missing frontend type exports for document detail models.
5. Align ADR file names to the implementation plan or update the plan references.
