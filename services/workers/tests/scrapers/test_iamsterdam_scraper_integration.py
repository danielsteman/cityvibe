"""Integration tests for Iamsterdam scraper against real website."""

import os

import httpx
import pytest
from cityvibe_core.models.venue import VenueBase
from loguru import logger
from workers.scrapers.iamsterdam_scraper import IamsterdamScraper

# Skip integration tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS", "false").lower() != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
)


@pytest.mark.integration
class TestIamsterdamScraperIntegration:
    """Integration tests that scrape the actual Iamsterdam website."""

    @pytest.mark.asyncio
    async def test_scrape_real_website(self):
        """Test scraping the actual Iamsterdam events page."""
        venue = VenueBase(
            name="Iamsterdam",
            website_url="https://www.iamsterdam.com/en/see-and-do/whats-on/events",
            city="Amsterdam",
            country="NL",
        )

        scraper = IamsterdamScraper(venue)

        # Actually scrape the website
        events = await scraper.scrape()

        # Basic assertions - website structure may vary
        assert isinstance(events, list), "Should return a list of events"

        # If events are found, validate their structure
        if events:
            for event in events:
                assert "title" in event, "Event should have a title"
                assert isinstance(event["title"], str), "Title should be a string"
                assert event["title"], "Title should not be empty"

                # start_time and source_url are optional but should be strings if present
                if "start_time" in event and event["start_time"] is not None:
                    assert isinstance(
                        event["start_time"], str
                    ), "start_time should be a string"

                if "source_url" in event and event["source_url"] is not None:
                    assert isinstance(
                        event["source_url"], str
                    ), "source_url should be a string"
                    assert event["source_url"].startswith(
                        "http"
                    ), "source_url should be a valid URL"

                if "description" in event and event["description"] is not None:
                    assert isinstance(
                        event["description"], str
                    ), "description should be a string"

                if "location" in event and event["location"] is not None:
                    assert isinstance(
                        event["location"], str
                    ), "location should be a string"

        # Log results for debugging
        logger.info(f"✅ Scraped {len(events)} events from Iamsterdam")
        if events:
            logger.debug(f"📝 Sample event: {events[0]}")

    @pytest.mark.asyncio
    async def test_scrape_single_event_page(self):
        """Test scraping a single event page from the real website."""
        venue = VenueBase(
            name="Iamsterdam",
            website_url="https://www.iamsterdam.com/en/see-and-do/whats-on/events",
            city="Amsterdam",
            country="NL",
        )

        scraper = IamsterdamScraper(venue)

        # Test scraping a single event page (using a sample URL from sitemap)
        # This test will fail if the URL structure changes, but validates the scraping logic
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Try to get URLs from sitemap first
            urls = await scraper._get_sitemap_urls()
            if not urls:
                pytest.skip("No event URLs found in sitemap")

            # Test scraping the first URL
            test_url = urls[0]
            event_data = await scraper._scrape_event_page(client, test_url)

            # Validate structure
            if event_data:
                assert event_data.get("kind") in ["Event", "Location"]
                assert event_data.get("title") or event_data.get("name"), "Should have a title or name"
                assert event_data.get("source_url"), "Should have source_url"
                logger.info(f"✅ Successfully scraped event: {event_data.get('title') or event_data.get('name')}")
            else:
                logger.warning(f"⚠️ No data extracted from {test_url}")

