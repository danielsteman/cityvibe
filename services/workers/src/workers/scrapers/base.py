"""Base scraper class with common functionality."""

from cityvibe_core.models.venue import Venue  # Will be created


class BaseScraper:
    """
    Abstract base scraper for extracting events from venue websites.

    All venue-specific scrapers should inherit from this class and implement
    the `scrape()` method to extract raw event data from the source.
    """

    def __init__(self, venue: Venue):
        """
        Initialize scraper with venue configuration.

        Args:
            venue: Venue model containing website URL and scraper config
        """
        self.venue = venue
        # TODO: Initialize rate limiter
        # self.rate_limiter = RateLimiter(venue.website_url)

    async def scrape(self) -> list[dict]:
        """
        Fetch and parse events from venue website.

        This method should:
        1. Fetch the website content (HTML, RSS, API, etc.)
        2. Parse the content to extract event information
        3. Return a list of raw event dictionaries

        Returns:
            List of raw event dictionaries. Each dict should contain:
            - title: str
            - description: str (optional)
            - start_time: str or datetime
            - source_url: str (URL to the event page)
            - Any other source-specific fields

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement scrape()")

    async def fetch_html(self, url: str) -> str:
        """
        Fetch HTML content from a URL with rate limiting and retries.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string
        """
        # TODO: Implement with httpx, rate limiting, retries
        # await self.rate_limiter.wait_if_needed()
        # response = await httpx.get(url)
        # return response.text

    async def parse_html(self, html: str) -> list[dict]:
        """
        Parse HTML to extract event information.

        This is a helper method that can be used by scrapers.
        For complex sites, scrapers may use Playwright instead.

        Args:
            html: HTML content to parse

        Returns:
            List of raw event dictionaries
        """
        # TODO: Implement with BeautifulSoup4
        # from bs4 import BeautifulSoup
        # soup = BeautifulSoup(html, 'html.parser')
        # # Extract events using selectors from venue.scraper_config
        # return events
