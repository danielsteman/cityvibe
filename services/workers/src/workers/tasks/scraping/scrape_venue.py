"""Celery task for scraping a single venue."""

from uuid import UUID

from celery import shared_task
from cityvibe_core.database.connection import init_db
from cityvibe_core.database.session import get_session
from cityvibe_core.models.venue import Venue
from loguru import logger
from sqlalchemy import select

from workers.scrapers.debuik_batch_scraper import DebuikScraper


@shared_task(name="workers.scrape_venue")
async def scrape_venue_task(venue_id: str | UUID) -> dict:
    """
    Scrape a single venue and process events through ETL pipeline.

    This is a Celery task that orchestrates:
    1. Fetch venue from database
    2. Run scraper to extract raw data
    3. Process events through ETL pipeline
    4. Save venue data to database

    Args:
        venue_id: UUID or string ID of the venue to scrape

    Returns:
        Dictionary with task results:
        {
            "venue_id": str,
            "venue_name": str,
            "events_found": int,
            "status": "success" | "failed",
            "error": str | None
        }
    """
    venue_id_str = str(venue_id)
    logger.info(f"🚀 Starting scrape task for venue: {venue_id_str}")

    # Initialize database connection
    init_db()

    try:
        async with get_session() as session:
            # Get venue from database
            venue = await session.get(Venue, venue_id)
            if not venue:
                error_msg = f"Venue {venue_id_str} not found"
                logger.error(f"❌ {error_msg}")
                return {
                    "venue_id": venue_id_str,
                    "status": "failed",
                    "error": error_msg,
                }

            logger.info(f"📊 Scraping venue: {venue.name} ({venue.website_url})")

            # Run scraper
            scraper = DebuikScraper(venue)
            scraped_data_list = await scraper.scrape()

            if not scraped_data_list or len(scraped_data_list) == 0:
                logger.warning(f"⚠️ No data scraped for venue: {venue.website_url}")
                return {
                    "venue_id": venue_id_str,
                    "venue_name": venue.name,
                    "events_found": 0,
                    "status": "success",
                    "error": None,
                }

            # For venue scraping, we get venue data (not events)
            # Update venue in database
            scraped_data = scraped_data_list[0]

            # Check if venue already exists by website_url
            result = await session.execute(
                select(Venue).where(Venue.website_url == scraped_data["website_url"])
            )
            existing_venue = result.scalar_one_or_none()

            if existing_venue and existing_venue.id != venue.id:
                logger.warning(
                    f"⚠️ Venue with website_url {scraped_data['website_url']} already exists"
                )
                return {
                    "venue_id": venue_id_str,
                    "venue_name": venue.name,
                    "status": "failed",
                    "error": "Venue with same website_url already exists",
                }

            # Update existing venue or create new one
            if existing_venue:
                logger.info(f"🔄 Updating existing venue: {existing_venue.name}")
                for key, value in scraped_data.items():
                    if hasattr(existing_venue, key):
                        setattr(existing_venue, key, value)
                await session.commit()
                logger.info(f"✅ Successfully updated venue: {existing_venue.name}")
                return {
                    "venue_id": str(existing_venue.id),
                    "venue_name": existing_venue.name,
                    "status": "success",
                    "error": None,
                }

            logger.info(f"✨ Creating new venue: {scraped_data.get('name', 'Unknown')}")
            new_venue = Venue(**scraped_data)
            session.add(new_venue)
            await session.commit()
            logger.info(f"✅ Successfully created venue: {new_venue.name}")
            return {
                "venue_id": str(new_venue.id),
                "venue_name": new_venue.name,
                "status": "success",
                "error": None,
            }

    except Exception as e:
        logger.exception(f"❌ Failed to scrape venue {venue_id_str}: {e}")
        return {
            "venue_id": venue_id_str,
            "status": "failed",
            "error": str(e),
        }


@shared_task(name="workers.scrape_venues_batch")
async def scrape_venues_batch_task(venue_ids: list[str | UUID]) -> dict:
    """
    Scrape multiple venues in batch.

    Args:
        venue_ids: List of venue IDs to scrape

    Returns:
        Dictionary with batch results:
        {
            "total": int,
            "successful": int,
            "failed": int,
            "results": list[dict]
        }
    """
    logger.info(f"🚀 Starting batch scrape for {len(venue_ids)} venues")

    results = []
    successful = 0
    failed = 0

    for venue_id in venue_ids:
        try:
            result = await scrape_venue_task(venue_id)
            results.append(result)
            if result["status"] == "success":
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.exception(f"❌ Failed to process venue {venue_id}: {e}")
            results.append(
                {
                    "venue_id": str(venue_id),
                    "status": "failed",
                    "error": str(e),
                }
            )
            failed += 1

    logger.info(f"✅ Batch scrape completed: {successful} successful, {failed} failed")
    return {
        "total": len(venue_ids),
        "successful": successful,
        "failed": failed,
        "results": results,
    }
