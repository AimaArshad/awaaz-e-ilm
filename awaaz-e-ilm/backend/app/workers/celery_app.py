"""Celery application configuration.

The Celery app is only used when `USE_CELERY=true`.
In development, BackgroundTasks (FastAPI) are used instead.

Workers are started with:
    celery -A app.workers.celery_app worker --loglevel=info
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "awaaz_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry failed tasks up to 3 times with exponential backoff
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    task_default_retry_delay=60,  # seconds
)
