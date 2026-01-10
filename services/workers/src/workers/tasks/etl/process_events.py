"""Celery task wrapper for processing events through ETL pipeline."""

from uuid import UUID

from celery import shared_task
from cityvibe_core.database.connection import init_db
from cityvibe_etl.event_processor import EventProcessor
from loguru import logger


@shared_task(name="workers.process_events")
async def process_events_task(venue_id: str | UUID, raw_events: list[dict]) -> dict:
    """
    Process raw events through the ETL pipeline.

    This task delegates to the cityvibe-etl package's EventProcessor
    to handle normalization, validation, deduplication, and enrichment.

    Args:
        venue_id: UUID or string ID of the venue these events belong to
        raw_events: List of raw event dictionaries from scraper

    Returns:
        Dictionary with processing results:
        {
            "venue_id": str,
            "events_processed": int,
            "events_new": int,
            "events_updated": int,
            "events_skipped": int,
            "errors": list[str],
            "status": "success" | "failed"
        }
    """
    venue_id_str = str(venue_id)
    logger.info(
        f"🚀 Starting ETL processing for venue {venue_id_str} with {len(raw_events)} events"
    )

    # Initialize database connection
    init_db()

    try:
        # Initialize ETL processor
        processor = EventProcessor()

        # Process events through ETL pipeline
        result = await processor.process(raw_events)

        logger.info(
            f"✅ ETL processing completed for venue {venue_id_str}: "
            f"{result.get('events_new', 0)} new, "
            f"{result.get('events_updated', 0)} updated"
        )

        return {
            "venue_id": venue_id_str,
            "status": "success",
            **result,
        }

    except Exception as e:
        logger.exception(f"❌ ETL processing failed for venue {venue_id_str}: {e}")
        return {
            "venue_id": venue_id_str,
            "status": "failed",
            "events_processed": 0,
            "events_new": 0,
            "events_updated": 0,
            "events_skipped": len(raw_events),
            "errors": [str(e)],
        }
