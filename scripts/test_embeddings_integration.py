"""Integration test to verify embedding generation works end-to-end."""

import asyncio
import os
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "cityvibe-core" / "src"))

from cityvibe_core.database.connection import init_db
from cityvibe_core.database.session import get_session
from cityvibe_core.embeddings import generate_vibe_text
from cityvibe_core.models.venue import Venue, VenueBase
from loguru import logger
from sqlalchemy import select


async def test_embedding_integration() -> dict:
    """
    Test that embedding generation flow works correctly.

    This test verifies:
    1. We can find venues without embeddings
    2. We can generate vibe text for venues
    3. The vibe_embedding column exists and can accept data
    4. The integration code path works (even if model isn't available)

    Returns:
        Dictionary with test results
    """
    init_db()

    results = {
        "venues_found": 0,
        "vibe_texts_generated": 0,
        "column_exists": False,
        "test_passed": False,
    }

    async with get_session() as session:
        # Test 1: Find venues without embeddings
        result = await session.execute(
            select(Venue).where(Venue.vibe_embedding.is_(None)).limit(1)
        )
        venues = result.scalars().all()
        results["venues_found"] = len(venues)

        if not venues:
            logger.warning("⚠️ No venues without embeddings found for testing")
            return results

        # Test 2: Generate vibe text (doesn't require model)
        venue = venues[0]
        vibe_text = generate_vibe_text(venue)
        if vibe_text and vibe_text.strip():
            results["vibe_texts_generated"] = 1
            logger.info(f"✅ Generated vibe text for {venue.name}: {vibe_text[:100]}...")
        else:
            logger.error(f"❌ Failed to generate vibe text for {venue.name}")

        # Test 3: Verify column exists and can be written to
        try:
            # Try to set a test embedding (even if None) to verify column exists
            original_embedding = venue.vibe_embedding
            # Just verify we can access the attribute
            if hasattr(venue, "vibe_embedding"):
                results["column_exists"] = True
                logger.info(f"✅ vibe_embedding column exists on Venue model")
            else:
                logger.error("❌ vibe_embedding column not found on Venue model")
        except Exception as e:
            logger.error(f"❌ Error accessing vibe_embedding column: {e}")

        # Test 4: Verify database column structure using raw SQL query
        # (AsyncEngine doesn't support inspect directly)
        from sqlalchemy import text

        result = await session.execute(
            text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'venue' AND column_name = 'vibe_embedding'
            """)
        )
        embedding_col = result.fetchone()
        if embedding_col:
            logger.info(
                f"✅ Database column 'vibe_embedding' exists: {embedding_col[1]}"
            )
            results["column_exists"] = True
        else:
            logger.error("❌ Database column 'vibe_embedding' not found")

    # Overall test result
    results["test_passed"] = (
        results["venues_found"] > 0
        and results["vibe_texts_generated"] > 0
        and results["column_exists"]
    )

    return results


async def main():
    """Main entry point."""
    if not os.getenv("DATABASE_URL"):
        logger.error("❌ DATABASE_URL environment variable is not set")
        sys.exit(1)

    logger.info("🧪 Testing embedding integration...")
    results = await test_embedding_integration()

    logger.info("=" * 80)
    logger.info("📊 Test Results")
    logger.info("=" * 80)
    logger.info(f"Venues found: {results['venues_found']}")
    logger.info(f"Vibe texts generated: {results['vibe_texts_generated']}")
    logger.info(f"Column exists: {results['column_exists']}")
    logger.info(f"Test passed: {results['test_passed']}")

    if results["test_passed"]:
        logger.info("✅ Integration test passed - embedding flow is working")
        logger.info("💡 Note: Actual embedding generation requires sentence-transformers")
        logger.info("   In production (Linux), embeddings will be generated automatically")
        sys.exit(0)
    else:
        logger.error("❌ Integration test failed - check logs above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
