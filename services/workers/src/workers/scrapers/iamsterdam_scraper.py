"""Iamsterdam scraper for extracting event data."""

from typing import Any


import json
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup
from loguru import logger


from workers.scrapers.base import BaseScraper


class IamsterdamScraper(BaseScraper):
    """
    Scraper for extracting events from Iamsterdam.

    Iamsterdam is the official tourism website for Amsterdam. This scraper extracts
    events, activities, and cultural happenings from the Iamsterdam website by:
    1. Discovering event URLs from the sitemap
    2. Scraping each event/location page to extract Next.js __NEXT_DATA__
    3. Normalizing the data into a consistent format
    """

    async def scrape(self) -> list[dict]:
        """
        Extract events from Iamsterdam by discovering URLs from sitemap and scraping them.

        Returns:
            List of raw event dictionaries. Each dict contains normalized event data
            with fields like: title, description, dates, location, images, etc.
        """
        logger.info(f"🚀 Starting scrape for Iamsterdam: {self.venue.website_url}")

        # Discover event URLs from sitemap
        event_urls = await self._get_sitemap_urls()
        logger.info(f"📊 Found {len(event_urls)} potential event/location URLs in sitemap")

        if not event_urls:
            logger.warning("⚠️ No event URLs found in sitemap")
            return []

        # Scrape each URL
        results = []
        processed_count = 0

        async with httpx.AsyncClient(timeout=15.0) as client:
            for url in event_urls:
                try:
                    event_data = await self._scrape_event_page(client, url)
                    if event_data:
                        results.append(event_data)
                        processed_count += 1

                    # Log progress every 50 items
                    if processed_count % 50 == 0:
                        logger.info(f"📝 Processed {processed_count}/{len(event_urls)} URLs...")
                except Exception as e:
                    logger.error(f"❌ Error scraping {url}: {e}")
                    continue

        logger.info(f"✅ Successfully scraped {len(results)} events from Iamsterdam")
        return results

    async def _get_sitemap_urls(self) -> list[str]:
        """
        Fetch sitemap and extract event/location URLs.

        Returns:
            List of URLs that point to event or location pages
        """
        sitemap_url = "https://www.iamsterdam.com/sitemap.xml"
        logger.debug(f"🔍 Fetching sitemap from: {sitemap_url}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(sitemap_url)
                response.raise_for_status()

            # Parse XML sitemap
            root = ET.fromstring(response.content)
            namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            all_urls = []

            for url_tag in root.findall("ns:url", namespace):
                loc_elem = url_tag.find("ns:loc", namespace)
                if loc_elem is not None:
                    loc = loc_elem.text
                    if loc is None:
                        continue

                    # Filter for event/location pages:
                    # - Must be in /uit/agenda/ (Dutch) or /whats-on/calendar/ (English)
                    # - Must be deep enough (exclude listing pages, usually 6+ segments)
                    if ("/uit/agenda/" in loc or "/whats-on/calendar/" in loc) and len(
                        loc.split("/")
                    ) > 6:
                        all_urls.append(loc)

            unique_urls = list[Any](set[Any](all_urls))
            logger.debug(f"🔍 Found {len(unique_urls)} unique event URLs in sitemap")
            return unique_urls

        except Exception as e:
            logger.error(f"❌ Critical error parsing sitemap: {e}")
            return []

    async def _scrape_event_page(
        self, client: httpx.AsyncClient, url: str
    ) -> dict | None:
        """
        Scrape a single event or location page to extract Next.js data.

        Args:
            client: httpx async client for making requests
            url: URL of the event/location page to scrape

        Returns:
            Normalized event/location dictionary or None if extraction fails
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }

            response = await client.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            script_tag = soup.find("script", id="__NEXT_DATA__")

            if not script_tag:
                logger.debug(f"⚠️ No __NEXT_DATA__ found in {url}")
                return None

            # Get script content - use get_text() for safety
            script_content = script_tag.get_text() if hasattr(script_tag, "get_text") else None
            if not script_content or not script_content.strip():
                logger.debug(f"⚠️ Empty __NEXT_DATA__ script content in {url}")
                return None

            json_obj = json.loads(script_content)
            page_props = json_obj.get("props", {}).get("pageProps", {}) or {}

            page_type = page_props.get("pageType", "Unknown")

            # Handle Event pages
            if page_type == "Event" or "event" in page_props or "Event" in page_props:
                event = (
                    page_props.get("event")
                    or page_props.get("Event")
                    or page_props.get("data")
                )
                if not event:
                    return None

                return self._normalize_event(event, page_props, url)

            # Handle Location pages (like AMAZE)
            if (
                page_type == "Location"
                or "Location" in page_props
                or "location" in page_props
            ):
                loc = page_props.get("Location") or page_props.get("location")

                # Fallback: some pages inline the location-like data on the root
                if not loc and "name" in page_props:
                    loc = page_props

                if not loc:
                    return None

                return self._normalize_location_as_event(loc, page_props, url)

            # Everything else is not relevant as event data
            return None

        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            return None

    def _normalize_location_as_event(
        self, loc: dict, page_props: dict, url: str
    ) -> dict:
        """
        Normalize a Location blocks to event-like structure.

        Args:
            loc: Location data dictionary
            page_props: Page properties from Next.js
            url: Source URL

        Returns:
            Normalized dictionary with location/visit-related fields
        """
        seo = page_props.get("seo", {})
        localizations = page_props.get("localizations", [])

        images = loc.get("images") or []
        main_image = images[0]["src"] if images else None

        address = loc.get("address") or {}
        coords = loc.get("coordinates") or {}

        # Extract dates from business hours or closed dates if available
        dates = None
        if loc.get("closedDates"):
            dates = loc.get("closedDates")
        elif loc.get("businessHours"):
            dates = loc.get("businessHours")

        return {
            "kind": "Location",
            "id": loc.get("id"),
            "ffID": loc.get("ffID"),
            "slug": loc.get("slug"),
            "title": loc.get("name"),
            "name": loc.get("name"),
            "category": loc.get("category", []),
            "directory": page_props.get("directory"),
            "pages": page_props.get("pages", []),
            "seo_title": seo.get("title"),
            "seo_description": seo.get("description"),
            "seo_slug": seo.get("slug"),
            "seo_og_image": seo.get("ogImage"),
            "localizations": localizations,
            "intro": loc.get("intro"),
            "description": loc.get("description"),
            "description_html": loc.get("description"),
            "main_image": main_image,
            "images": images,
            "alwaysOpen": loc.get("alwaysOpen"),
            "closedDates": loc.get("closedDates"),
            "businessHours": loc.get("businessHours", {}),
            "openUntil": loc.get("openUntil"),
            "soldOut": loc.get("soldOut"),
            "address": {
                "street": address.get("street"),
                "houseNumber": address.get("houseNumber"),
                "zipcode": address.get("zipcode"),
                "city": address.get("city"),
            },
            "coordinates": {
                "lat": coords.get("latitude"),
                "lng": coords.get("longitude"),
            },
            "phoneNumber": loc.get("phoneNumber"),
            "email": loc.get("email"),
            "urls": loc.get("urls", []),
            "promotions": loc.get("promotions", []),
            "dates": dates,
            "source_url": url,
        }

    def _normalize_event(self, event: dict, page_props: dict, url: str) -> dict:
        """
        Normalize real Event pages to match the schema.

        Args:
            event: Event data dictionary
            page_props: Page properties from Next.js
            url: Source URL

        Returns:
            Normalized dictionary with event fields
        """
        seo = page_props.get("seo", {})
        localizations = page_props.get("localizations", [])

        images = event.get("images") or []
        main_image = images[0]["src"] if images else None

        # Extract title (can be in different fields)
        title = event.get("title") or event.get("name") or seo.get("title")

        return {
            "kind": "Event",
            "id": event.get("id"),
            "slug": event.get("slug"),
            "title": title,
            "name": title,
            "directory": page_props.get("directory"),
            "pages": page_props.get("pages", []),
            "seo_title": seo.get("title"),
            "seo_description": seo.get("description"),
            "seo_slug": seo.get("slug"),
            "seo_og_image": seo.get("ogImage"),
            "localizations": localizations,
            "intro": event.get("intro"),
            "description": event.get("description"),
            "description_html": event.get("description"),
            "main_image": main_image,
            "images": images,
            "dates": event.get("date") or event.get("dates"),
            "highlights": event.get("highlights", []),
            "source_url": url,
        }

