from celery import Celery

from app.core.config import settings

celery_app = Celery(
	"docflow",
	broker=settings.celery_broker_url,
	backend=settings.celery_result_backend,
)

celery_app.conf.update(
	task_serializer="json",
	result_serializer="json",
	accept_content=["json"],
	timezone="UTC",
	enable_utc=True,
	task_track_started=True,
	task_acks_late=False,
	worker_prefetch_multiplier=1,
)

# Discover `app.workers.tasks` by scanning the `app.workers` package.
# Using `related_name="tasks"` avoids trying to import a non-existent
# `app.workers.tasks.tasks` module.
celery_app.autodiscover_tasks(["app.workers"], related_name="tasks", force=True)
