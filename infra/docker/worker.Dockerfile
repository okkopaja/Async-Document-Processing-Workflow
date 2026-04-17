FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /workspace/apps/api

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libmagic1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY apps/api/pyproject.toml /workspace/apps/api/pyproject.toml
COPY apps/api/README.md /workspace/apps/api/README.md

RUN uv sync --no-dev

COPY apps/api /workspace/apps/api

CMD ["uv", "run", "celery", "-A", "app.core.celery_app.celery_app", "worker", "--loglevel=info"]
