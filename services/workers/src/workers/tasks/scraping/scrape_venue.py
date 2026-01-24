"""Celery task for scraping a single venue."""

from uuid import UUID, uuid4

from celery import shared_task
from cityvibe_core.database.connection import init_db
from cityvibe_core.database.session import get_session
from cityvibe_core.embeddings import generate_vibe_text, get_embeddings
from cityvibe_core.models.venue import Venue
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

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
            # Update venue in database using PostgreSQL native upsert
            scraped_data = scraped_data_list[0]

            website_url = scraped_data.get("website_url")
            if not website_url:
                logger.error("❌ Scraped data missing website_url")
                return {
                    "venue_id": venue_id_str,
                    "venue_name": venue.name,
                    "status": "failed",
                    "error": "Scraped data missing website_url",
                }

            # Check if venue already exists by website_url (for validation)
            result = await session.execute(
                select(Venue.id).where(Venue.website_url == website_url)
            )
            existing_venue_id = result.scalar_one_or_none()

            if existing_venue_id and existing_venue_id != venue.id:
                logger.warning(
                    f"⚠️ Venue with website_url {website_url} already exists with different ID"
                )
                return {
                    "venue_id": venue_id_str,
                    "venue_name": venue.name,
                    "status": "failed",
                    "error": "Venue with same website_url already exists",
                }

            # Check if venue exists and has embedding before upsert
            result = await session.execute(
                select(Venue.id, Venue.vibe_embedding).where(
                    Venue.website_url == website_url
                )
            )
            existing_row = result.first()
            was_existing = existing_row is not None
            existing_embedding = existing_row[1] if existing_row else None

            # Prepare data for insert (exclude created_at, updated_at, vibe_embedding)
            # Generate UUID for id if not present (for new inserts)
            insert_data = {
                k: v
                for k, v in scraped_data.items()
                if k not in ("created_at", "updated_at", "vibe_embedding")
            }
            # Generate UUID for new inserts if id is not in the data
            if "id" not in insert_data:
                insert_data["id"] = uuid4()

            # Use PostgreSQL native UPSERT with ON CONFLICT DO UPDATE
            # Preserve vibe_embedding if it already exists
            # Don't update id, created_at, or website_url on conflict
            update_dict = {
                k: v
                for k, v in insert_data.items()
                if k not in ("id", "website_url", "created_at")  # Don't update these on conflict
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
            upserted_venue_id = upserted_row[0] if upserted_row else None
            current_embedding = upserted_row[1] if upserted_row else None

            if not upserted_venue_id:
                logger.error(f"❌ Failed to upsert venue: {website_url}")
                return {
                    "venue_id": venue_id_str,
                    "venue_name": venue.name,
                    "status": "failed",
                    "error": "Failed to upsert venue",
                }

            # Commit the upsert first
            await session.commit()

            # Track action
            action = "updated" if was_existing else "created"
            logger.info(f"✅ Successfully {action} venue: {scraped_data.get('name', 'Unknown')}")

            # Initialize embeddings model (lazy-loaded, cached) - optional
            embeddings_model = None
            try:
                embeddings_model = get_embeddings()
                logger.debug("✅ Embeddings model available")
            except Exception as e:
                logger.warning(
                    f"⚠️ Embeddings model not available: {e}. "
                    f"Venue will be saved without embeddings."
                )

            # Check if embedding is needed
            needs_embedding = current_embedding is None

            # Generate embedding if needed and model is available
            if needs_embedding and embeddings_model:
                try:
                    # Fetch the full venue object for embedding generation
                    venue_obj = await session.get(Venue, upserted_venue_id)
                    if not venue_obj:
                        logger.warning(
                            f"⚠️ Could not fetch venue {upserted_venue_id} for embedding"
                        )
                    else:
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
                        f"❌ Failed to generate embedding for venue {upserted_venue_id}: {e}"
                    )
                    # Continue without embedding - venue will still be saved
            elif needs_embedding and not embeddings_model:
                logger.debug(
                    f"⏭️ Skipping embedding for venue {upserted_venue_id} (embeddings not available)"
                )

            # Fetch venue for return value
            venue_obj = await session.get(Venue, upserted_venue_id)
            if not venue_obj:
                return {
                    "venue_id": venue_id_str,
                    "venue_name": venue.name,
                    "status": "failed",
                    "error": "Could not fetch upserted venue",
                }

            return {
                "venue_id": str(venue_obj.id),
                "venue_name": venue_obj.name,
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
