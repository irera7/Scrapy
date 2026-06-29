from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "ai_collector",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    task_routes={
        "app.workers.tasks.run_scraping_job": {"queue": "scraping"},
        "app.workers.tasks.run_export_task": {"queue": "exports"},
        "app.workers.tasks.process_data_item": {"queue": "processing"},
    },
    beat_schedule={
        "check-scheduled-jobs": {
            "task": "app.workers.tasks.check_scheduled_jobs",
            "schedule": 60.0,  # Every minute
        },
    },
)

