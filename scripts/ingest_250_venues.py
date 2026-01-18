"""Script to ingest 250 venues from both Debuik and Iamsterdam scrapers."""

import asyncio
import csv
import os
import sys
from pathlib import Path

from loguru import logger

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"📁 Loaded environment variables from {env_path}")
except ImportError:
    pass

from workers.tasks.scraping.scrape_source import (
    scrape_debuik_source_task,
    scrape_iamsterdam_source_task,
)


def load_debuik_urls(csv_path: Path, limit: int = 250) -> list[str]:
    """
    Load Debuik URLs from CSV file.

    Args:
        csv_path: Path to the CSV file with Debuik URLs
        limit: Maximum number of URLs to load

    Returns:
        List of unique URLs
    """
    urls = []
    seen = set()

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("URL", "").strip()
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)
                    if len(urls) >= limit:
                        break
    except Exception as e:
        logger.error(f"❌ Failed to load Debuik URLs from {csv_path}: {e}")
        raise

    logger.info(f"📥 Loaded {len(urls)} unique Debuik URLs from {csv_path}")
    return urls


async def main():
    """Main function to ingest 250 venues from each source."""
    # Check DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable is not set")
        logger.info(
            "💡 Set it with: export DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/cityvibe'"
        )
        sys.exit(1)

    logger.info("🚀 Starting venue ingestion: 250 records from each source")
    logger.info(
        f"📊 Database: {database_url.split('@')[-1] if '@' in database_url else 'configured'}"
    )
    logger.info("💡 Note: This will take ~35-40 minutes (scraping with Playwright is slow)")
    logger.info("💡 Embeddings are generated during scraping for each venue")

    results = {}

    # Get project root
    project_root = Path(__file__).parent.parent
    debuik_csv = project_root / "notebooks" / "restaurant_urls" / "debuik_links.csv"

    # Ingest 250 Debuik venues
    logger.info("\n" + "=" * 80)
    logger.info("📋 Ingesting 250 Debuik venues")
    logger.info("=" * 80)

    try:
        debuik_urls = load_debuik_urls(debuik_csv, limit=250)
        logger.info(f"🔗 Scraping {len(debuik_urls)} Debuik URLs...")

        debuik_result = await scrape_debuik_source_task(debuik_urls)
        results["debuik"] = debuik_result

        logger.info(f"\n✅ Debuik ingestion completed: {debuik_result['status']}")
        if debuik_result["status"] == "success":
            save_stats = debuik_result["venues_saved"]
            logger.info(f"   📊 Total processed: {save_stats.get('total', 0)}")
            logger.info(f"   ✨ Created: {save_stats.get('created', 0)}")
            logger.info(f"   🔄 Updated: {save_stats.get('updated', 0)}")
            logger.info(f"   ❌ Failed: {save_stats.get('failed', 0)}")
        else:
            logger.error(f"   ❌ Error: {debuik_result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.exception(f"❌ Debuik ingestion failed with exception: {e}")
        results["debuik"] = {"status": "failed", "error": str(e)}

    # Ingest 250 Iamsterdam venues
    logger.info("\n" + "=" * 80)
    logger.info("📋 Ingesting 250 Iamsterdam venues")
    logger.info("=" * 80)

    try:
        logger.info(f"🔗 Scraping up to 250 Iamsterdam venues from sitemap...")

        iamsterdam_result = await scrape_iamsterdam_source_task(limit=250)
        results["iamsterdam"] = iamsterdam_result

        logger.info(f"\n✅ Iamsterdam ingestion completed: {iamsterdam_result['status']}")
        if iamsterdam_result["status"] == "success":
            save_stats = iamsterdam_result["venues_saved"]
            logger.info(
                f"   📊 Venues discovered: {iamsterdam_result.get('venues_discovered', 0)}"
            )
            logger.info(f"   📊 Total processed: {save_stats.get('total', 0)}")
            logger.info(f"   ✨ Created: {save_stats.get('created', 0)}")
            logger.info(f"   🔄 Updated: {save_stats.get('updated', 0)}")
            logger.info(f"   ❌ Failed: {save_stats.get('failed', 0)}")
        else:
            logger.error(
                f"   ❌ Error: {iamsterdam_result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.exception(f"❌ Iamsterdam ingestion failed with exception: {e}")
        results["iamsterdam"] = {"status": "failed", "error": str(e)}

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 Ingestion Summary")
    logger.info("=" * 80)

    debuik_success = results.get("debuik", {}).get("status") == "success"
    iamsterdam_success = results.get("iamsterdam", {}).get("status") == "success"

    if debuik_success:
        debuik_stats = results["debuik"]["venues_saved"]
        logger.info(
            f"✅ Debuik: {debuik_stats.get('created', 0)} created, "
            f"{debuik_stats.get('updated', 0)} updated"
        )
    else:
        logger.error(f"❌ Debuik: Failed - {results.get('debuik', {}).get('error', 'Unknown')}")

    if iamsterdam_success:
        iamsterdam_stats = results["iamsterdam"]["venues_saved"]
        logger.info(
            f"✅ Iamsterdam: {iamsterdam_stats.get('created', 0)} created, "
            f"{iamsterdam_stats.get('updated', 0)} updated"
        )
    else:
        logger.error(
            f"❌ Iamsterdam: Failed - {results.get('iamsterdam', {}).get('error', 'Unknown')}"
        )

    # Check embeddings
    logger.info("\n" + "=" * 80)
    logger.info("🔍 Checking embedding generation")
    logger.info("=" * 80)

    total_venues = 0
    if debuik_success:
        total_venues += results["debuik"]["venues_saved"].get("total", 0)
    if iamsterdam_success:
        total_venues += results["iamsterdam"]["venues_saved"].get("total", 0)

    logger.info(f"💡 Total venues processed: {total_venues}")
    logger.info(
        "💡 Embeddings are generated during scraping if the embedding model is available"
    )
    logger.info("💡 To check embeddings in database:")
    logger.info(
        "   docker-compose exec postgres psql -U postgres -d cityvibe -c "
        "\"SELECT COUNT(*) as total, COUNT(vibe_embedding) as with_embedding "
        "FROM venue;\""
    )


if __name__ == "__main__":
    asyncio.run(main())
