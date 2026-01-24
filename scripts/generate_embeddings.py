"""Script to generate embeddings for venues (missing or regenerate all)."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "cityvibe-core" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "workers" / "src"))

from cityvibe_core.database.connection import init_db
from cityvibe_core.database.session import get_session
from cityvibe_core.embeddings import generate_vibe_text, get_embeddings
from cityvibe_core.models.venue import Venue
from loguru import logger
from sqlalchemy import select


async def generate_missing_embeddings(
    limit: int | None = None,
    regenerate: bool = False,
) -> dict:
    """
    Generate embeddings for venues that are missing them, or regenerate all.

    Args:
        limit: Optional limit on number of venues to process.
        regenerate: If True, process all venues and overwrite existing embeddings.
            Use after updating generate_vibe_text (e.g. adding cuisine) to improve RAG.

    Returns:
        Dictionary with processing statistics.
    """
    init_db()

    try:
        embeddings_model = get_embeddings()
        logger.info("✅ Embeddings model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load embeddings model: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "processed": 0,
            "generated": 0,
            "failed": 0,
        }

    processed = 0
    generated = 0
    failed = 0

    async with get_session() as session:
        if regenerate:
            result = await session.execute(
                select(Venue).order_by(Venue.created_at)
            )
            venues = result.scalars().all()
        else:
            result = await session.execute(
                select(Venue).where(Venue.vibe_embedding.is_(None)).order_by(Venue.created_at)
            )
            venues = result.scalars().all()

        if limit:
            venues = venues[:limit]
        total = len(venues)

        if regenerate:
            logger.info(f"📊 Regenerating embeddings for {total} venues")
        else:
            logger.info(f"📊 Processing {total} venues missing embeddings")

        for venue in venues:
            try:
                processed += 1

                # Generate vibe text
                vibe_text = generate_vibe_text(venue)
                if not vibe_text or not vibe_text.strip():
                    logger.warning(f"⚠️ Empty vibe text for venue: {venue.name}")
                    failed += 1
                    continue

                # Generate embedding
                logger.debug(f"📊 Generating embedding for venue: {venue.name} ({processed}/{total})")
                embedding = embeddings_model.embed_query(vibe_text)

                if embedding and len(embedding) > 0:
                    venue.vibe_embedding = embedding
                    generated += 1
                    logger.debug(f"✅ Generated embedding for venue: {venue.name}")
                else:
                    logger.warning(f"⚠️ Empty embedding for venue: {venue.name}")
                    failed += 1

                # Commit periodically (every 10 venues)
                if processed % 10 == 0:
                    await session.commit()
                    logger.info(f"💾 Progress: {processed}/{total} processed, {generated} generated")

            except Exception as e:
                logger.error(f"❌ Failed to generate embedding for venue {venue.name}: {e}")
                failed += 1
                continue

        # Final commit
        await session.commit()

    logger.info(
        f"✅ Embedding generation complete: {processed} processed, "
        f"{generated} generated, {failed} failed"
    )

    return {
        "status": "success",
        "processed": processed,
        "generated": generated,
        "failed": failed,
    }


async def main():
    """Main entry point."""
    if not os.getenv("DATABASE_URL"):
        logger.error("❌ DATABASE_URL environment variable is not set")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Generate embeddings for venues.")
    parser.add_argument(
        "limit",
        nargs="?",
        type=int,
        default=None,
        help="Max number of venues to process (default: all)",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate embeddings for all venues (overwrite existing). "
        "Use after updating vibe text (e.g. adding cuisine) to improve RAG.",
    )
    args = parser.parse_args()

    result = await generate_missing_embeddings(limit=args.limit, regenerate=args.regenerate)

    if result["status"] == "success":
        logger.info("✅ Successfully completed embedding generation")
        sys.exit(0)
    else:
        logger.error(f"❌ Embedding generation failed: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
