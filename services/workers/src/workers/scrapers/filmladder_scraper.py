"""Filmladder scraper for extracting event data."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright

from workers.scrapers.base import BaseScraper


class FilmladderScraper(BaseScraper):
    """
    Scraper for extracting events from Filmladder.

    Filmladder is a Dutch cinema listing website. This scraper extracts
    film showtimes and event information from the Amsterdam cinemas page.
    """

    async def scrape(self) -> list[dict]:
        """
        Extract events from Filmladder.

        Returns:
            List of raw event dictionaries. Each dict should contain:
            - title: str (film title)
            - description: str (optional, film description)
            - start_time: str or datetime (showtime)
            - source_url: str (URL to the event page)
            - venue_name: str (cinema name)
            - Any other source-specific fields
        """
        url = self.venue.website_url

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html = await page.content()
                events = await self._parse_html(html, url)
            finally:
                await browser.close()

        return events

    async def _parse_html(self, html: str, base_url: str) -> list[dict]:
        """
        Parse HTML content to extract event information.

        Args:
            html: HTML content from the Filmladder page
            base_url: Base URL for constructing absolute links

        Returns:
            List of raw event dictionaries
        """
        if not html or not html.strip():
            return []

        soup = BeautifulSoup(html, "html.parser")
        events = []

        # Try multiple selector patterns to handle different page structures
        # Pattern 1: Cinema sections with films listed underneath (most common)
        cinema_selectors = [
            ".cinema",
            ".bioscoop",
            ".venue",
            '[class*="cinema"]',
            '[class*="bioscoop"]',
            '[class*="venue"]',
            "section.cinema",
            "div.cinema-section",
        ]

        film_selectors = [
            ".film",
            ".movie",
            ".showing",
            ".event",
            '[class*="film"]',
            '[class*="movie"]',
            '[class*="showing"]',
        ]

        # Try to find cinema sections first
        cinemas = None
        for selector in cinema_selectors:
            cinemas = soup.select(selector)
            if cinemas:
                break

        if cinemas:
            # Parse cinema-by-cinema structure
            for cinema in cinemas:
                # Extract venue name
                venue_name = None
                venue_selectors = [".cinema-name", "h2", "h3", ".venue-name", ".name"]
                for vs in venue_selectors:
                    venue_elem = cinema.select_one(vs)
                    if venue_elem:
                        venue_name = venue_elem.get_text(strip=True)
                        break

                # If no venue name found, try to get it from parent or use default
                if not venue_name:
                    venue_name = self.venue.name or "Unknown Venue"

                # Find film items within this cinema
                film_items = None
                for selector in film_selectors:
                    film_items = cinema.select(selector)
                    if film_items:
                        break

                if film_items:
                    for item in film_items:
                        event = self._extract_event_data(item, venue_name, base_url)
                        if event:
                            events.append(event)
        else:
            # Pattern 2: Films listed directly on the page (no cinema grouping)
            # Try all selectors and combine results (items might use different classes)
            all_film_items = []
            seen_items = set()
            for selector in film_selectors:
                found_items = soup.select(selector)
                for item in found_items:
                    # Use id to deduplicate if same element found by multiple selectors
                    item_id = id(item)
                    if item_id not in seen_items:
                        seen_items.add(item_id)
                        all_film_items.append(item)

            if all_film_items:
                venue_name = self.venue.name or "Unknown Venue"
                for item in all_film_items:
                    event = self._extract_event_data(item, venue_name, base_url)
                    if event:
                        events.append(event)

        return events

    def _extract_event_data(
        self, item: Tag, venue_name: str, base_url: str
    ) -> dict | None:
        """
        Extract event data from a single film/item element.

        Args:
            item: BeautifulSoup element containing film/showing information
            venue_name: Name of the venue/cinema
            base_url: Base URL for constructing absolute links

        Returns:
            Dictionary with event data or None if extraction fails
        """
        # Extract title
        title = None
        title_selectors = [".title", "h3", "h4", ".film-title", ".movie-title", "a"]
        for ts in title_selectors:
            title_elem = item.select_one(ts)
            if title_elem:
                title = title_elem.get_text(strip=True)
                # If it's a link, prefer the link text
                if title_elem.name == "a" and title:
                    break
                if title:
                    break

        if not title:
            return None

        # Extract start time/showtime
        start_time = None
        time_selectors = [".time", ".showtime", "time", ".start-time", "[datetime]"]
        for ts in time_selectors:
            time_elem = item.select_one(ts)
            if time_elem:
                # Try datetime attribute first
                start_time = time_elem.get("datetime") or time_elem.get_text(strip=True)
                if start_time:
                    break

        # Extract source URL
        source_url = None
        link_elem = item.select_one("a[href]")
        if link_elem:
            href = link_elem.get("href", "")
            if href and isinstance(href, str):
                source_url = (
                    urljoin(base_url, href) if not href.startswith("http") else href
                )

        # Extract description
        description = None
        desc_selectors = [".description", ".synopsis", ".summary", ".film-description"]
        for ds in desc_selectors:
            desc_elem = item.select_one(ds)
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                if description:
                    break

        return {
            "title": title,
            "start_time": start_time,
            "source_url": source_url,
            "venue_name": venue_name,
            "description": description,
        }
