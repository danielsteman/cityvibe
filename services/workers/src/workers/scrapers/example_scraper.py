"""Example scraper implementation for reference."""

from workers.scrapers.base import BaseScraper


class ExampleVenueScraper(BaseScraper):
    """
    Example scraper showing how to extract events from a venue website.

    This is a template for creating new scrapers. Replace with actual
    venue-specific logic.
    """

    async def scrape(self) -> list[dict]:
        """
        Extract events from the venue website.

        This example shows a simple HTML scraping approach.
        For JavaScript-heavy sites, use Playwright instead.
        """
        # Option 1: Simple HTML scraping
        html = await self.fetch_html(self.venue.website_url)
        events = await self.parse_html(html)

        # Option 2: Use Playwright for JS-heavy sites
        # from playwright.async_api import async_playwright
        # async with async_playwright() as p:
        #     browser = await p.chromium.launch()
        #     page = await browser.new_page()
        #     await page.goto(self.venue.website_url)
        #     # Extract events using page.selectors
        #     events = await self.extract_events_from_page(page)
        #     await browser.close()

        # Option 3: Use Scrapy for structured sites with sitemaps
        # (Can be configured per venue)

        # Return raw events as dictionaries
        # The ETL pipeline will normalize, validate, deduplicate, and enrich
        return events

    async def extract_events_from_page(self, page) -> list[dict]:
        """
        Extract events from a Playwright page object.

        Args:
            page: Playwright page object

        Returns:
            List of raw event dictionaries
        """
        # TODO: Implement event extraction logic
        # events = []
        # event_elements = await page.query_selector_all('.event-item')
        # for element in event_elements:
        #     title = await element.query_selector('.title').inner_text()
        #     # ... extract other fields
        #     events.append({
        #         "title": title,
        #         "source_url": await element.get_attribute('href'),
        #         # ... other fields
        #     })
        # return events
        return []
