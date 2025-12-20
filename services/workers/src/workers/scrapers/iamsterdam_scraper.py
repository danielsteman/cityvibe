"""Iamsterdam scraper for extracting venue data."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, UTC
from typing import Any

import httpx
from bs4 import BeautifulSoup
from geoalchemy2 import WKTElement
from loguru import logger

from cityvibe_core.models.venue import OpeningHours, VenueLink
from workers.scrapers.base import BaseScraper
from deep_translator import GoogleTranslator

# Initialize translator
translator = GoogleTranslator(source="nl", target="en")


class IamsterdamScraper(BaseScraper):
    """
    Scraper for extracting venue data from Iamsterdam.

    Iamsterdam is the official tourism website for Amsterdam. This scraper extracts
    venue information from location pages by:
    1. Discovering venue URLs from the sitemap
    2. Scraping each location page to extract Next.js __NEXT_DATA__
    3. Converting the data to Venue objects with translation
    All Dutch content is automatically translated to English.
    """

    def _translate_text(self, text: str, max_retries: int = 3) -> str:
        """
        Translate Dutch text to English with retry logic.

        Args:
            text: Dutch text to translate
            max_retries: Maximum number of retry attempts

        Returns:
            Translated English text, or original text if translation fails
        """
        if not translator or not text or not isinstance(text, str) or not text.strip():
            return text

        for attempt in range(max_retries):
            try:
                translated = translator.translate(text)
                return translated if translated else text
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                logger.warning(f"⚠️ Translation failed for '{text[:50]}...': {e}")
                return text

        return text

    def _convert_business_hours_to_opening_hours(
        self, business_hours: dict
    ) -> list[OpeningHours]:
        """
        Convert iamsterdam businessHours format to OpeningHours objects.

        Args:
            business_hours: Dictionary with business hours data

        Returns:
            List of OpeningHours objects
        """
        opening_hours_list = []

        if not business_hours:
            return opening_hours_list

        # Day name mapping
        day_mapping = {
            "monday": "monday",
            "tuesday": "tuesday",
            "wednesday": "wednesday",
            "thursday": "thursday",
            "friday": "friday",
            "saturday": "saturday",
            "sunday": "sunday",
            "maandag": "monday",
            "dinsdag": "tuesday",
            "woensdag": "wednesday",
            "donderdag": "thursday",
            "vrijdag": "friday",
            "zaterdag": "saturday",
            "zondag": "sunday",
        }

        regular_hours = business_hours.get("regularHours") or []
        if not isinstance(regular_hours, list):
            regular_hours = []

        for day_data in regular_hours:
            day_name = day_data.get("day", "").lower()
            eng_day = day_mapping.get(day_name, day_name) or "monday"

            if day_data.get("closed") or day_data.get("isClosed"):
                opening_hours_list.append(OpeningHours(day=eng_day, is_closed=True))
            else:
                opens = day_data.get("opens") or day_data.get("open")
                closes = day_data.get("closes") or day_data.get("close")
                if opens and closes:
                    opening_hours_list.append(
                        OpeningHours(day=eng_day, opens=str(opens), closes=str(closes))
                    )
                else:
                    opening_hours_list.append(OpeningHours(day=eng_day, is_closed=True))

        return opening_hours_list

    async def scrape(self) -> list[dict]:
        """
        Extract venue data from Iamsterdam by discovering URLs from sitemap and scraping them.

        Returns:
            List of venue dictionaries matching Venue model structure.
        """
        logger.info(f"🚀 Starting scrape for Iamsterdam: {self.venue.website_url}")

        # Discover venue URLs from sitemap
        venue_urls = await self._get_sitemap_urls()
        logger.info(f"📊 Found {len(venue_urls)} potential venue URLs in sitemap")

        if not venue_urls:
            logger.warning("⚠️ No venue URLs found in sitemap")
            return []

        # Scrape each URL
        results = []
        processed_count = 0

        async with httpx.AsyncClient(timeout=15.0) as client:
            for url in venue_urls:
                try:
                    venue_data = await self._scrape_event_page(client, url)
                    if venue_data:
                        results.append(venue_data)
                        processed_count += 1

                    # Log progress every 50 items
                    if processed_count % 50 == 0:
                        logger.info(f"📝 Processed {processed_count}/{len(venue_urls)} URLs...")
                except Exception as e:
                    logger.error(f"❌ Error scraping {url}: {e}")
                    continue

        logger.info(f"✅ Successfully scraped {len(results)} venues from Iamsterdam")
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

    async def _scrape_event_page(self, client: httpx.AsyncClient, url: str) -> dict | None:
        """
        Scrape a single location page to extract Next.js data and convert to Venue format.

        Args:
            client: httpx async client for making requests
            url: URL of the location page to scrape

        Returns:
            Venue dictionary matching Venue model structure or None if extraction fails
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

            # Handle Location pages (venues)
            if page_type == "Location" or "Location" in page_props or "location" in page_props:
                loc = page_props.get("Location") or page_props.get("location")

                # Fallback: some pages inline the location-like data on the root
                if not loc and "name" in page_props:
                    loc = page_props

                if not loc:
                    return None

                return self._normalize_location_as_venue(loc, page_props, url)

            # Event pages are not venues, skip them
            return None

        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            return None

    def _normalize_location_as_venue(self, loc: dict, page_props: dict, url: str) -> dict | None:
        """
        Convert a Location block to a Venue dictionary.

        Args:
            loc: Location data dictionary
            page_props: Page properties from iamsterdam
            url: Source URL

        Returns:
            Venue dictionary matching Venue model structure or None if required data is missing
        """
        seo = page_props.get("seo", {})
        localizations = page_props.get("localizations", [])

        # Extract basic info
        name = loc.get("name")
        if not name:
            return None

        images = loc.get("images") or []
        main_image = images[0]["src"] if images else None

        address = loc.get("address") or {}
        coords = loc.get("coordinates") or {}

        lat = coords.get("latitude")
        lon = coords.get("longitude")

        if lat is None or lon is None:
            return None

        # Extract and translate description
        description_html = loc.get("description") or seo.get("description")
        description_text = None
        if description_html:
            # Strip HTML tags for plain text description
            soup = BeautifulSoup(description_html, "html.parser")
            description_text = soup.get_text(separator=" ", strip=True)
            description_text = (
                self._translate_text(description_text) if description_text else None
            )

        # Extract venue type from category
        categories = loc.get("category") or []
        if not isinstance(categories, list):
            categories = []
        venue_type = categories[0] if categories and len(categories) > 0 else None
        if venue_type:
            # Handle dict category format (iamsterdam sometimes uses dicts)
            if isinstance(venue_type, dict):
                venue_type = (
                    venue_type.get("title") or venue_type.get("name") or None
                )
            if venue_type:
                venue_type = self._translate_text(str(venue_type))

        # Convert business hours
        business_hours = loc.get("businessHours") or {}
        if not isinstance(business_hours, dict):
            business_hours = {}
        opening_hours = self._convert_business_hours_to_opening_hours(business_hours)

        # Convert URLs to VenueLink objects
        urls = loc.get("urls") or []
        if not isinstance(urls, list):
            urls = []
        external_links = []
        website_url = url  # Default to source URL
        for url_obj in urls:
            if isinstance(url_obj, dict):
                link_url = url_obj.get("url") or url_obj.get("href")
                link_label = url_obj.get("label") or url_obj.get("type", "Website")
                if link_url:
                    external_links.append(VenueLink(label=link_label, url=link_url))
                    if link_label.lower() in ["website", "homepage", "home"]:
                        website_url = link_url
            elif isinstance(url_obj, str):
                external_links.append(VenueLink(label="Website", url=url_obj))
                website_url = url_obj

        # Extract tags from category
        tags = []
        if categories:
            for cat in categories:
                if isinstance(cat, dict):
                    # Handle dict category format
                    cat_text = cat.get("title") or cat.get("name") or cat.get("slug")
                    if cat_text:
                        tags.append(self._translate_text(str(cat_text)))
                elif isinstance(cat, str):
                    tags.append(self._translate_text(cat))

        # Build features dict
        features = {
            "address": f"{address.get('street', '')} {address.get('houseNumber', '')}".strip(),
            "zipcode": address.get("zipcode"),
            "image_url": main_image,
            "phone": loc.get("phoneNumber"),
            "email": loc.get("email"),
            "always_open": loc.get("alwaysOpen", False),
            "closed_dates": loc.get("closedDates") or [],
            "open_until": loc.get("openUntil"),
        }

        # Create PostGIS POINT for location (longitude, latitude order)
        location_point = WKTElement(f"POINT({lon} {lat})", srid=4326)

        # Build scraper config
        config = {
            "source": "iamsterdam.com",
            "original_url": url,
            "scraped_at": datetime.now(UTC).isoformat(),
            "iamsterdam_id": loc.get("id"),
            "ffID": loc.get("ffID"),
            "slug": loc.get("slug"),
            "original": {
                "description": description_html,
                "venue_type": categories[0] if categories and len(categories) > 0 else None,
                "category": categories,
                "business_hours": business_hours,
                "tags": categories,
            },
            "translated": {
                "description": description_text,
                "venue_type": venue_type,
                "tags": tags,
            },
            "seo": {
                "title": seo.get("title"),
                "description": seo.get("description"),
                "slug": seo.get("slug"),
                "og_image": seo.get("ogImage"),
            },
            "localizations": localizations,
            "images": images,
            "promotions": loc.get("promotions", []),
        }

        return {
            "name": name,
            "description": description_text,
            "website_url": website_url,
            "city": address.get("city", "Amsterdam"),
            "state": "Noord-Holland",
            "country": "NL",
            "latitude": float(lat),
            "longitude": float(lon),
            "location": location_point,
            "venue_type": venue_type,
            "tags": tags,
            "opening_hours": opening_hours,
            "external_links": external_links,
            "features": features,
            "scraper_config": config,
            "source": "iamsterdam",
            "last_scraped_at": datetime.now(UTC),
            "active": True,
        }

