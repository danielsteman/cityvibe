"""Celery app initialization for workers service."""

from celery import Celery
from loguru import logger

# Create Celery app
celery_app = Celery(
    "cityvibe_workers",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Import tasks to register them
# This ensures tasks are discovered by Celery
try:
    from workers.tasks.etl.process_events import process_events_task  # noqa: F401
    from workers.tasks.scraping.scrape_source import (  # noqa: F401
        scrape_debuik_source_task,
        scrape_iamsterdam_source_task,
    )
    from workers.tasks.scraping.scrape_venue import (  # noqa: F401
        scrape_venue_task,
        scrape_venues_batch_task,
    )

    logger.info("✅ Celery tasks registered successfully")
except ImportError as e:
    logger.warning(f"⚠️ Some tasks could not be imported: {e}")


def create_app() -> Celery:
    """
    Create and configure Celery app.

    Returns:
        Configured Celery app instance
    """
    return celery_app


if __name__ == "__main__":
    celery_app.start()
