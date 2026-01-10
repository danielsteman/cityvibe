"""Quick test script to run tasks locally."""

import asyncio
import sys

from workers.tasks.scraping.scrape_venue import scrape_venue_task


async def main():
    """Test running a scrape task."""
    if len(sys.argv) < 2:
        print("Usage: python test_task.py <venue_id>")
        print("Example: python test_task.py 123e4567-e89b-12d3-a456-426614174000")
        print()
        print("💡 First create a venue:")
        print('   python create_venue.py "https://www.debuik.nl/restaurant/123"')
        print("   python create_venue.py --list  # List existing venues")
        sys.exit(1)

    venue_id = sys.argv[1]
    print(f"🚀 Running scrape task for venue: {venue_id}")

    # Call task directly (without Celery)
    result = await scrape_venue_task(venue_id)
    print(f"✅ Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
