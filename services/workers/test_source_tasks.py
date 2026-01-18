"""Test script for running source scraping tasks with a subset of data."""

import asyncio
import json
import os
import sys

from loguru import logger

from workers.tasks.scraping.scrape_source import (
    scrape_debuik_source_task,
    scrape_iamsterdam_source_task,
)


async def main():
    """Test running source scraping tasks with a subset of data."""
    # Check DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable is not set")
        logger.info("💡 Set it with: export DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/cityvibe'")
        sys.exit(1)

    logger.info("🚀 Starting source task tests with subset of data")
    logger.info(f"📊 Database: {database_url.split('@')[-1] if '@' in database_url else 'configured'}")

    results = {}

    # Test Debuik scraper with 3 URLs
    logger.info("\n" + "=" * 80)
    logger.info("📋 Testing Debuik Source Task (3 URLs)")
    logger.info("=" * 80)

    debuik_urls = [
        "https://www.debuik.nl/amsterdam/restaurant/petitbysam",
        "https://www.debuik.nl/amsterdam/restaurant/restaurant-blauw",
        "https://www.debuik.nl/amsterdam/restaurant/de-kas",
    ]

    logger.info(f"🔗 URLs to scrape: {len(debuik_urls)}")
    for url in debuik_urls:
        logger.info(f"   - {url}")

    try:
        debuik_result = await scrape_debuik_source_task(debuik_urls)
        results["debuik"] = debuik_result
        logger.info(f"\n✅ Debuik task completed: {debuik_result['status']}")
        if debuik_result["status"] == "success":
            save_stats = debuik_result["venues_saved"]
            logger.info(f"   📊 Created: {save_stats.get('created', 0)}")
            logger.info(f"   🔄 Updated: {save_stats.get('updated', 0)}")
            logger.info(f"   ❌ Failed: {save_stats.get('failed', 0)}")
        else:
            logger.error(f"   ❌ Error: {debuik_result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.exception(f"❌ Debuik task failed with exception: {e}")
        results["debuik"] = {"status": "failed", "error": str(e)}

    # Test Iamsterdam scraper with limit of 3
    logger.info("\n" + "=" * 80)
    logger.info("📋 Testing Iamsterdam Source Task (limit: 3 venues)")
    logger.info("=" * 80)

    try:
        iamsterdam_result = await scrape_iamsterdam_source_task(limit=3)
        results["iamsterdam"] = iamsterdam_result
        logger.info(f"\n✅ Iamsterdam task completed: {iamsterdam_result['status']}")
        if iamsterdam_result["status"] == "success":
            save_stats = iamsterdam_result["venues_saved"]
            logger.info(f"   📊 Discovered: {iamsterdam_result.get('venues_discovered', 0)}")
            logger.info(f"   📊 Created: {save_stats.get('created', 0)}")
            logger.info(f"   🔄 Updated: {save_stats.get('updated', 0)}")
            logger.info(f"   ❌ Failed: {save_stats.get('failed', 0)}")
        else:
            logger.error(f"   ❌ Error: {iamsterdam_result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.exception(f"❌ Iamsterdam task failed with exception: {e}")
        results["iamsterdam"] = {"status": "failed", "error": str(e)}

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 Test Summary")
    logger.info("=" * 80)
    logger.info(json.dumps(results, indent=2, default=str))

    logger.info("\n💡 Check the database in pgAdmin (http://localhost:5050) to verify results")
    logger.info("   - Login: admin@cityvibe.com / admin")
    logger.info("   - Connect to: postgres@localhost:5432 / cityvibe")


if __name__ == "__main__":
    asyncio.run(main())
