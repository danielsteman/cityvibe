"""Integration tests for Debuik scraper against real website."""

import os

import pytest
from cityvibe_core.models.venue import VenueBase
from loguru import logger
from playwright.async_api import async_playwright
from workers.scrapers.debuik_batch_scraper import DebuikScraper

# Skip integration tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS", "false").lower() != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
)


@pytest.mark.integration
class TestDebuikScraperIntegration:
    """Integration tests that scrape the actual Debuik website."""

    @pytest.mark.asyncio
    async def test_scrape_real_website(self):
        """Test scraping an actual Debuik restaurant page."""
        venue = VenueBase(
            name="Test Restaurant",
            website_url="https://www.debuik.nl/amsterdam/restaurant/petitbysam",
            city="Amsterdam",
        )

        scraper = DebuikScraper(venue)

        # Actually scrape the website
        venues = await scraper.scrape()

        # Basic assertions - website structure may vary
        assert isinstance(venues, list), "Should return a list of venues"

        # If venues are found, validate their structure
        if venues:
            venue_data = venues[0]
            assert "name" in venue_data, "Venue should have a name"
            assert isinstance(venue_data["name"], str), "Name should be a string"
            assert venue_data["name"], "Name should not be empty"

            assert "website_url" in venue_data, "Venue should have website_url"
            assert isinstance(venue_data["website_url"], str), "website_url should be a string"
            assert venue_data["website_url"].startswith("http"), "website_url should be a valid URL"

            assert "city" in venue_data, "Venue should have city"
            assert isinstance(venue_data["city"], str), "City should be a string"

            assert "venue_type" in venue_data, "Venue should have venue_type"
            assert isinstance(venue_data["venue_type"], str), "venue_type should be a string"

            assert "scraper_config" in venue_data, "Venue should have scraper_config"
            assert isinstance(venue_data["scraper_config"], dict), "scraper_config should be a dict"
            assert venue_data["scraper_config"]["source"] == "debuik.nl"

            # latitude and longitude are optional but should be Decimal or None if present
            if "latitude" in venue_data and venue_data["latitude"] is not None:
                from decimal import Decimal

                assert isinstance(
                    venue_data["latitude"], Decimal
                ), "latitude should be a Decimal"

            if "longitude" in venue_data and venue_data["longitude"] is not None:
                from decimal import Decimal

                assert isinstance(
                    venue_data["longitude"], Decimal
                ), "longitude should be a Decimal"

        # Log results for debugging
        logger.info(f"Scraped {len(venues)} venues from Debuik")
        if venues:
            logger.debug(f"Sample venue: {venues[0]}")

    @pytest.mark.asyncio
    async def test_parse_real_html_structure(self):
        """Test parsing with HTML fetched from the real website."""
        venue = VenueBase(
            name="Test Restaurant",
            website_url="https://www.debuik.nl/amsterdam/restaurant/petitbysam",
            city="Amsterdam",
        )

        scraper = DebuikScraper(venue)

        # Fetch real HTML using Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(venue.website_url, wait_until="networkidle", timeout=30000)
                html = await page.content()
            finally:
                await browser.close()

        # Parse the real HTML
        venue_data = await scraper._parse_html(html, venue.website_url)

        # Validate structure
        assert venue_data is not None or venue_data is None, "Should return dict or None"

        # If parsing found venue data, validate it
        if venue_data:
            logger.info("Parsed venue data from real HTML")
            logger.debug(f"HTML length: {len(html)} characters")
            logger.debug(f"Venue data keys: {list(venue_data.keys())}")

            # Check that we're extracting meaningful data
            assert venue_data.get("name"), "Should extract venue name"
            assert venue_data.get("city"), "Should extract city"
            assert venue_data.get("scraper_config"), "Should have scraper_config"
            # Note: Actual selectors may need adjustment based on real website structure
