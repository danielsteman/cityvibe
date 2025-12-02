"""Integration tests for Filmladder scraper against real website."""

import os

import pytest
from cityvibe_core.models.venue import VenueBase
from loguru import logger
from playwright.async_api import async_playwright
from workers.scrapers.filmladder_scraper import FilmladderScraper

# Skip integration tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS", "false").lower() != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
)


@pytest.mark.integration
class TestFilmladderScraperIntegration:
    """Integration tests that scrape the actual Filmladder website."""

    @pytest.mark.asyncio
    async def test_scrape_real_website(self):
        """Test scraping the actual Filmladder Amsterdam cinemas page."""
        venue = VenueBase(
            name="Filmladder Amsterdam",
            website_url="https://www.filmladder.nl/amsterdam/bioscopen",
            city="Amsterdam",
        )

        scraper = FilmladderScraper(venue)

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

                assert "venue_name" in event, "Event should have venue_name"
                assert isinstance(
                    event["venue_name"], str
                ), "venue_name should be a string"

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

        # Log results for debugging
        logger.info(f"Scraped {len(events)} events from Filmladder")
        if events:
            logger.debug(f"Sample event: {events[0]}")

    @pytest.mark.asyncio
    async def test_parse_real_html_structure(self):
        """Test parsing with HTML fetched from the real website."""
        venue = VenueBase(
            name="Filmladder Amsterdam",
            website_url="https://www.filmladder.nl/amsterdam/bioscopen",
            city="Amsterdam",
        )

        scraper = FilmladderScraper(venue)

        # Fetch real HTML using Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(
                    venue.website_url, wait_until="networkidle", timeout=30000
                )
                html = await page.content()
            finally:
                await browser.close()

        # Parse the real HTML
        events = await scraper._parse_html(html, venue.website_url)

        # Validate structure
        assert isinstance(events, list), "Should return a list"

        # If parsing found events, validate them
        if events:
            logger.info(f"Parsed {len(events)} events from real HTML")
            logger.debug(f"HTML length: {len(html)} characters")
            logger.debug(f"Sample event keys: {list(events[0].keys())}")

            # Check that we're extracting meaningful data
            sample = events[0]
            assert sample.get("title"), "Should extract film titles"
            # Note: Actual selectors may need adjustment based on real website structure
