"""Celery tasks for scraping venue sources (Debuik, Iamsterdam, etc.)."""

from datetime import datetime

from celery import shared_task
from cityvibe_core.database.connection import init_db
from cityvibe_core.database.session import get_session
from cityvibe_core.embeddings import generate_vibe_text, get_embeddings
from cityvibe_core.models.venue import OpeningHours, Venue, VenueBase, VenueLink
from geoalchemy2 import WKTElement
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from workers.scrapers.debuik_batch_scraper import DebuikScraper
from workers.scrapers.iamsterdam_scraper import IamsterdamScraper


def _convert_venue_data_for_db(venue_data: dict) -> dict:
    """
    Convert venue data dictionary to format suitable for database storage.

    Converts OpeningHours and VenueLink objects to dictionaries for JSONB storage.

    Args:
        venue_data: Venue data dictionary from scraper

    Returns:
        Dictionary with SQLModel objects converted to dictionaries
    """
    converted_data = venue_data.copy()

    # Convert OpeningHours objects to dictionaries
    if "opening_hours" in converted_data and converted_data["opening_hours"]:
        opening_hours = converted_data["opening_hours"]
        if opening_hours and isinstance(opening_hours[0], OpeningHours):
            converted_data["opening_hours"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in opening_hours
            ]

    # Convert VenueLink objects to dictionaries
    if "external_links" in converted_data and converted_data["external_links"]:
        external_links = converted_data["external_links"]
        if external_links and isinstance(external_links[0], VenueLink):
            converted_data["external_links"] = [
                item.model_dump() if hasattr(item, "model_dump") else dict(item)
                for item in external_links
            ]

    # Convert timezone-aware datetime to naive datetime for last_scraped_at
    # (database column is TIMESTAMP WITHOUT TIME ZONE)
    if "last_scraped_at" in converted_data and converted_data["last_scraped_at"]:
        dt = converted_data["last_scraped_at"]
        if isinstance(dt, datetime) and dt.tzinfo is not None:
            converted_data["last_scraped_at"] = dt.replace(tzinfo=None)

    return converted_data


async def _save_venue_dicts(venue_dicts: list[dict], source: str) -> dict:
    """
    Save or update venues from scraper dictionaries.

    This function handles cases where venues may or may not exist in the database.
    It performs an upsert operation: creates new venues if they don't exist,
    or updates existing venues if they do (matched by website_url).
    Also generates embeddings for venues that need them.

    Args:
        venue_dicts: List of venue dictionaries from scrapers
        source: Source identifier (e.g., "debuik", "iamsterdam")

    Returns:
        Dictionary with save statistics:
        {
            "total": int,
            "created": int,
            "updated": int,
            "failed": int
        }
    """
    if not venue_dicts:
        return {"total": 0, "created": 0, "updated": 0, "failed": 0}

    init_db()
    created = 0
    updated = 0
    failed = 0

    # Initialize embeddings model (lazy-loaded, cached) - optional
    # If sentence-transformers is not available, embeddings will be skipped
    embeddings_model = None
    try:
        embeddings_model = get_embeddings()
        logger.debug("✅ Embeddings model available")
    except Exception as e:
        logger.warning(
            f"⚠️ Embeddings model not available: {e}. "
            f"Venues will be saved without embeddings."
        )

    async with get_session() as session:
        for venue_data in venue_dicts:
            try:
                website_url = venue_data.get("website_url")
                if not website_url:
                    logger.warning("⚠️ Skipping venue with missing website_url")
                    failed += 1
                    continue

                # Convert SQLModel objects to dictionaries for JSONB storage
                converted_data = _convert_venue_data_for_db(venue_data)

                # Check if venue exists before upsert to track created vs updated
                result = await session.execute(
                    select(Venue.id, Venue.vibe_embedding).where(
                        Venue.website_url == website_url
                    )
                )
                existing_row = result.first()
                was_existing = existing_row is not None
                existing_embedding = existing_row[1] if existing_row else None

                # Prepare data for insert (exclude id, created_at, updated_at, vibe_embedding)
                # These are handled by the database or preserved on conflict
                insert_data = {
                    k: v
                    for k, v in converted_data.items()
                    if k not in ("id", "created_at", "updated_at", "vibe_embedding")
                }

                # Use PostgreSQL native UPSERT with ON CONFLICT DO UPDATE
                # Preserve vibe_embedding if it already exists (don't overwrite existing embeddings)
                update_dict = {
                    k: v
                    for k, v in insert_data.items()
                    if k != "website_url"  # Don't update the conflict key
                }
                # Preserve existing vibe_embedding on conflict
                update_dict["vibe_embedding"] = Venue.__table__.c.vibe_embedding

                stmt = (
                    insert(Venue.__table__)
                    .values(**insert_data)
                    .on_conflict_do_update(
                        index_elements=["website_url"],
                        set_=update_dict,
                    )
                    .returning(Venue.__table__.c.id, Venue.__table__.c.vibe_embedding)
                )

                # Execute upsert and get the returned row
                result = await session.execute(stmt)
                upserted_row = result.first()
                venue_id = upserted_row[0] if upserted_row else None
                current_embedding = upserted_row[1] if upserted_row else None

                if not venue_id:
                    logger.error(f"❌ Failed to upsert venue: {website_url}")
                    failed += 1
                    continue

                # Commit the upsert first
                await session.commit()

                # Track created vs updated
                if was_existing:
                    updated += 1
                    logger.debug(f"🔄 Updated venue: {converted_data.get('name', 'Unknown')}")
                else:
                    created += 1
                    logger.debug(f"✨ Created venue: {converted_data.get('name', 'Unknown')}")

                # Check if embedding is needed
                needs_embedding = current_embedding is None

                # Generate embedding if needed and model is available
                if needs_embedding and embeddings_model:
                    try:
                        # Fetch the full venue object for embedding generation
                        venue_obj = await session.get(Venue, venue_id)
                        if not venue_obj:
                            logger.warning(f"⚠️ Could not fetch venue {venue_id} for embedding")
                            continue

                        # Generate vibe text from venue data
                        vibe_text = generate_vibe_text(venue_obj)
                        if vibe_text and vibe_text.strip():
                            logger.debug(
                                f"📊 Generating embedding for venue: {venue_obj.name}"
                            )
                            # Generate embedding (synchronous operation)
                            embedding = embeddings_model.embed_query(vibe_text)
                            if embedding:
                                venue_obj.vibe_embedding = embedding
                                await session.commit()
                                logger.debug(
                                    f"✅ Generated embedding for venue: {venue_obj.name}"
                                )
                            else:
                                logger.warning(
                                    f"⚠️ Empty embedding generated for venue: {venue_obj.name}"
                                )
                        else:
                            logger.warning(f"⚠️ Empty vibe text for venue: {venue_obj.name}")
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to generate embedding for venue {venue_id}: {e}"
                        )
                        # Continue without embedding - venue will still be saved
                elif needs_embedding and not embeddings_model:
                    logger.debug(
                        f"⏭️ Skipping embedding for venue {venue_id} (embeddings not available)"
                    )

            except Exception as e:
                logger.error(f"❌ Failed to save venue: {e}")
                failed += 1
                await session.rollback()
                continue

    logger.info(
        f"💾 Saved venues: {created} created, {updated} updated, {failed} failed"
    )
    return {
        "total": len(venue_dicts),
        "created": created,
        "updated": updated,
        "failed": failed,
    }


@shared_task(name="workers.scrape_debuik_source")
async def scrape_debuik_source_task(venue_urls: list[str] | None = None) -> dict:
    """
    Scrape Debuik source and save venues to database.

    This task can be run periodically to update Debuik venues.
    For each URL, it creates a minimal VenueBase, runs the scraper,
    and saves/updates the venue in the database.

    This task works even when no venues exist in the database yet.
    It will create new venues or update existing ones (matched by website_url).

    Args:
        venue_urls: Optional list of specific URLs to scrape.
                   If None, task should fail (Debuik requires specific URLs).

    Returns:
        Dictionary with task results:
        {
            "source": "debuik",
            "status": "success" | "failed",
            "urls_processed": int,
            "venues_saved": dict,
            "error": str | None
        }
    """
    logger.info("🚀 Starting Debuik source scrape task")

    if not venue_urls:
        error_msg = "Debuik scraper requires venue URLs to be provided"
        logger.error(f"❌ {error_msg}")
        return {
            "source": "debuik",
            "status": "failed",
            "urls_processed": 0,
            "venues_saved": {},
            "error": error_msg,
        }

    init_db()

    try:
        all_venue_dicts = []

        # Create minimal VenueBase objects and run scrapers
        for url in venue_urls:
            try:
                # Create minimal VenueBase for scraper initialization
                venue_base = VenueBase(
                    name="Temp",  # Will be replaced by scraper
                    website_url=url,
                    city="Amsterdam",
                    state="Noord-Holland",
                    country="NL",
                    latitude=52.3676,  # Amsterdam center (will be updated)
                    longitude=4.9041,
                    active=True,
                )

                scraper = DebuikScraper(venue_base)
                venue_dicts = await scraper.scrape()

                if venue_dicts:
                    all_venue_dicts.extend(venue_dicts)

            except Exception as e:
                logger.error(f"❌ Error scraping {url}: {e}")
                continue

        # Save all venues to database
        save_stats = await _save_venue_dicts(all_venue_dicts, "debuik")

        logger.info(f"✅ Debuik source scrape completed: {save_stats['total']} venues")
        return {
            "source": "debuik",
            "status": "success",
            "urls_processed": len(venue_urls),
            "venues_saved": save_stats,
            "error": None,
        }

    except Exception as e:
        logger.exception(f"❌ Failed Debuik source scrape: {e}")
        return {
            "source": "debuik",
            "status": "failed",
            "urls_processed": 0,
            "venues_saved": {},
            "error": str(e),
        }


@shared_task(name="workers.scrape_iamsterdam_source")
async def scrape_iamsterdam_source_task(
    sitemap_url: str | None = None, limit: int | None = None
) -> dict:
    """
    Scrape Iamsterdam source and save venues to database.

    This task can be run periodically to discover and update Iamsterdam venues.
    It creates a minimal VenueBase, runs the IamsterdamScraper (which discovers
    URLs from sitemap), and saves/updates all venues in the database.

    This task works even when no venues exist in the database yet.
    It will discover venues from the sitemap, create new venues, or update
    existing ones (matched by website_url).

    Args:
        sitemap_url: Optional sitemap URL (defaults to Iamsterdam scraper default).
        limit: Optional limit on number of venues to scrape (for testing).
               If None, scrapes all discovered venues.

    Returns:
        Dictionary with task results:
        {
            "source": "iamsterdam",
            "status": "success" | "failed",
            "venues_discovered": int,
            "venues_saved": dict,
            "error": str | None
        }
    """
    logger.info("🚀 Starting Iamsterdam source scrape task")

    init_db()

    try:
        # Create minimal VenueBase for scraper initialization
        # IamsterdamScraper discovers URLs from sitemap, so website_url is just for logging
        venue_base = VenueBase(
            name="Iamsterdam Source",
            website_url="https://www.iamsterdam.com",  # Used only for logging
            city="Amsterdam",
            state="Noord-Holland",
            country="NL",
            latitude=52.3676,
            longitude=4.9041,
            active=True,
        )

        scraper = IamsterdamScraper(venue_base)
        venue_dicts = await scraper.scrape(limit=limit)

        # Save all venues to database
        save_stats = await _save_venue_dicts(venue_dicts, "iamsterdam")

        logger.info(
            f"✅ Iamsterdam source scrape completed: {save_stats['total']} venues"
        )
        return {
            "source": "iamsterdam",
            "status": "success",
            "venues_discovered": len(venue_dicts),
            "venues_saved": save_stats,
            "error": None,
        }

    except Exception as e:
        logger.exception(f"❌ Failed Iamsterdam source scrape: {e}")
        return {
            "source": "iamsterdam",
            "status": "failed",
            "venues_discovered": 0,
            "venues_saved": {},
            "error": str(e),
        }
