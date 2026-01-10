"""Debuik scraper for extracting venue data."""

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup
from cityvibe_core.models.venue import OpeningHours, VenueLink
from deep_translator import GoogleTranslator
from geoalchemy2 import WKTElement
from loguru import logger
from playwright.async_api import async_playwright

from workers.scrapers.base import BaseScraper

# Initialize translator
translator = GoogleTranslator(source="nl", target="en")

# Constants for standardization
DUTCH_TO_ENG_DAYS = {
    "Maandag": "monday",
    "Dinsdag": "tuesday",
    "Woensdag": "wednesday",
    "Donderdag": "thursday",
    "Vrijdag": "friday",
    "Zaterdag": "saturday",
    "Zondag": "sunday",
}

PRICE_MAP = {
    "Kleine prijs": "€",
    "Gemiddeld": "€€",
    "Luxe": "€€€",
}


class DebuikScraper(BaseScraper):
    """
    Scraper for extracting venue data from Debuik.

    Debuik is a Dutch restaurant listing website. This scraper extracts
    venue information including address, opening hours, features, and location.
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

    def _translate_dict_keys_values(self, d: dict) -> dict:
        """
        Translate both keys and values of a dictionary from Dutch to English.

        Args:
            d: Dictionary with Dutch keys and/or values

        Returns:
            Dictionary with translated keys and values
        """
        if not d:
            return d

        translated = {}
        for key, value in d.items():
            translated_key = self._translate_text(str(key))
            if isinstance(value, str):
                translated_value = self._translate_text(value)
            elif isinstance(value, list):
                translated_value = [
                    self._translate_text(str(v)) if isinstance(v, str) else v for v in value
                ]
            elif isinstance(value, dict):
                translated_value = self._translate_dict_keys_values(value)
            else:
                translated_value = value
            translated[translated_key] = translated_value

        return translated

    async def scrape(self) -> list[dict]:
        """
        Extract venue data from Debuik.

        Returns:
            List containing a single venue dictionary with venue data.
            Each dict contains:
            - name: str
            - website_url: str
            - city: str
            - state: str
            - country: str
            - latitude: Decimal | None
            - longitude: Decimal | None
            - venue_type: str
            - scraper_config: dict
            - active: bool
        """
        url = self.venue.website_url

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html = await page.content()
                venue_data = await self._parse_html(html, url)
            finally:
                await browser.close()

        return [venue_data] if venue_data else []

    async def _parse_html(self, html: str, url: str) -> dict | None:
        """
        Parse HTML content to extract venue information.

        Args:
            html: HTML content from the Debuik page
            url: URL of the venue page

        Returns:
            Dictionary with venue data or None if parsing fails
        """
        if not html or not html.strip():
            return None

        soup = BeautifulSoup(html, "html.parser")

        # Extract basic info
        addr_info = self._extract_address_info(soup)
        if not addr_info["name"]:
            return None

        # Extract all data
        lat_dec, lon_dec = self._extract_lat_lon(soup)
        if lat_dec is None or lon_dec is None:
            return None

        lat, lon = float(lat_dec), float(lon_dec)
        venue_type, raw_features = self._extract_venue_features(soup)
        raw_hours = self._extract_opening_hours(soup)
        description = self._extract_description(soup)
        image_url = self._extract_image(soup)
        tags = self._extract_tags(soup)

        # Translate content from Dutch to English
        logger.info("🌐 Translating content from Dutch to English...")
        translated_description = self._translate_text(description) if description else None
        translated_tags = [self._translate_text(tag) for tag in tags] if tags else []
        translated_features = self._translate_dict_keys_values(raw_features) if raw_features else {}
        translated_venue_type = self._translate_text(venue_type) if venue_type else None

        # Standardize opening hours to OpeningHours objects
        structured_hours = []
        for d_day, d_time in raw_hours.items():
            eng_day = DUTCH_TO_ENG_DAYS.get(d_day)
            if not eng_day:
                continue
            if d_time in ["Gesloten", "Closed", "Unknown"]:
                structured_hours.append(OpeningHours(day=eng_day, is_closed=True))
            else:
                try:
                    start, end = d_time.split(" - ")
                    structured_hours.append(OpeningHours(day=eng_day, opens=start, closes=end))
                except Exception:
                    structured_hours.append(OpeningHours(day=eng_day, is_closed=True))

        # Find external website (fallback to own URL if no external link)
        external_website = None
        sidebar = soup.select_one(".restaurant-contactvlak")
        if sidebar:
            for a in sidebar.find_all("a", href=True):
                if "website" in a.get_text().lower() and "debuik.nl" not in a["href"]:
                    external_website = a["href"]
                    break

        final_url = external_website if external_website else url

        # Convert external_links to list of VenueLink objects
        external_links_list = []
        if final_url:
            external_links_list.append(VenueLink(label="Website", url=final_url))

        # Create PostGIS POINT for location (longitude, latitude order)
        location_point = WKTElement(f"POINT({lon} {lat})", srid=4326)

        # Build translated features dict
        translated_features_dict = {
            "address": f"{addr_info['street']}, {addr_info['zip_code']}",
            "image_url": image_url,
        }
        # Add all translated features (keys and values are already translated)
        if translated_features:
            for key, value in translated_features.items():
                # Normalize key to snake_case
                normalized_key = key.lower().replace(" ", "_")
                translated_features_dict[normalized_key] = value

        # Construct scraper config with both original and translated data
        config = {
            "source": "debuik.nl",
            "original_url": url,
            "scraped_at": datetime.now(UTC).isoformat(),
            "street": addr_info["street"],
            "zip_code": addr_info["zip_code"],
            "image_url": image_url,
            "original": {
                "description": description,
                "venue_type": venue_type,
                "features": raw_features,
                "opening_hours": raw_hours,
                "tags": tags,
            },
            "translated": {
                "description": translated_description,
                "venue_type": translated_venue_type,
                "features": translated_features,
                "opening_hours": raw_hours,  # Time format is same, days already mapped
                "tags": translated_tags,
            },
        }

        return {
            "name": addr_info["name"],
            "description": translated_description,
            "website_url": final_url,
            "city": addr_info.get("city") or "Amsterdam",
            "state": "Noord-Holland",
            "country": "NL",
            "latitude": lat,
            "longitude": lon,
            "location": location_point,
            "venue_type": translated_venue_type,
            "price_range": PRICE_MAP.get(raw_features.get("Prijsniveau", ""), "€€"),
            "tags": list(set(translated_tags)),
            "opening_hours": structured_hours,
            "external_links": external_links_list,
            "features": translated_features_dict,
            "scraper_config": config,
            "source": "debuik",
            "last_scraped_at": datetime.now(UTC),
            "active": True,
        }

    def _extract_address_info(self, soup: BeautifulSoup) -> dict[str, str | None]:
        """
        Extract address information from the venue page.

        Args:
            soup: BeautifulSoup object of the parsed HTML

        Returns:
            Dictionary with name, street, zip_code, and city
        """
        info = {"name": None, "street": None, "zip_code": None, "city": "Amsterdam"}

        # Try the .address div (Server Side Rendered)
        address_div = soup.select_one("div.address")
        if address_div:
            h1 = address_div.find("h1")
            if h1:
                info["name"] = h1.get_text(strip=True)
            street_elem = address_div.select_one(".street")
            if street_elem:
                info["street"] = street_elem.get_text(strip=True)
            postcode_elem = address_div.select_one(".postcode")
            if postcode_elem:
                info["zip_code"] = postcode_elem.get_text(strip=True)
            city_elem = address_div.select_one(".city")
            if city_elem:
                info["city"] = city_elem.get_text(strip=True)

        # Fallback: Search for H1 if the div structure is different
        if not info["name"]:
            h1 = soup.find("h1")
            if h1:
                info["name"] = h1.get_text(strip=True)

        return info

    def _extract_description(self, soup: BeautifulSoup) -> str | None:
        """
        Extract venue description from the page.

        Args:
            soup: BeautifulSoup object of the parsed HTML

        Returns:
            Description text or None if not found
        """
        intro = soup.select_one(".introductie")
        if intro:
            return intro.get_text(separator=" ", strip=True)
        return None

    def _extract_image(self, soup: BeautifulSoup) -> str | None:
        """
        Extract venue image URL from the page.

        Args:
            soup: BeautifulSoup object of the parsed HTML

        Returns:
            Image URL or None if not found
        """
        # Slideshow image
        img = soup.select_one(".restaurant-slideshow .restaurant-slide img.imgfade-transition")
        if img:
            src = img.get("src")
            if src and isinstance(src, str):
                return src
        # Thumbnail fallback
        thumb = soup.select_one(".thumbnails img")
        if thumb:
            src = thumb.get("src")
            if src and isinstance(src, str):
                return src
        return None

    def _extract_lat_lon(self, soup: BeautifulSoup) -> tuple[Decimal | None, Decimal | None]:
        """
        Extract latitude and longitude from Google Maps images in the HTML.

        Args:
            soup: BeautifulSoup object of the parsed HTML

        Returns:
            Tuple of (latitude, longitude) or (None, None) if not found
        """
        url_to_check = None
        map_img = soup.select_one(".locatie-small img")
        if map_img:
            url_to_check = map_img.get("src")

        if not url_to_check:
            map_div = soup.select_one(".locatie-large a")
            if map_div:
                url_to_check = map_div.get("style")

        if url_to_check:
            match = re.search(r"center=([\d\.]+),([\d\.]+)", str(url_to_check))
            if match:
                try:
                    return Decimal(match.group(1)), Decimal(match.group(2))
                except (InvalidOperation, ValueError):
                    pass
        return None, None

    def _extract_opening_hours(self, soup: BeautifulSoup) -> dict[str, str]:
        """
        Parse the HTML table with opening hours.

        Args:
            soup: BeautifulSoup object of the parsed HTML

        Returns:
            Dictionary mapping day names to opening hours
        """
        hours = {}
        table = soup.select_one(".openingstijden-tabel")
        if not table:
            return hours

        for row in table.select(".openingstijden-tabel-tr"):
            day_div = row.select_one(".openingstijden-label div")
            if not day_div:
                continue
            day = day_div.get_text(strip=True)

            data_div = row.select_one(".openingstijden-data")
            if not data_div:
                continue

            if data_div.select_one(".openingstijden-gesloten"):
                hours[day] = "Closed"
            else:
                time_div = data_div.select_one(".openingstijden-restaurant")
                if time_div:
                    start_elem = time_div.select_one(".start")
                    end_elem = time_div.select_one(".einde")
                    s = start_elem.get_text(strip=True) if start_elem else "?"
                    e = end_elem.get_text(strip=True) if end_elem else "?"
                    hours[day] = f"{s} - {e}"
                else:
                    hours[day] = "Unknown"
        return hours

    def _extract_venue_features(self, soup: BeautifulSoup) -> tuple[str, dict[str, str]]:
        """
        Extract venue type and list of features.

        Args:
            soup: BeautifulSoup object of the parsed HTML

        Returns:
            Tuple of (venue_type, features_dict)
        """
        venue_type = "Restaurant"
        features = {}
        kenmerken_div = soup.select_one(".kenmerken .content")
        if kenmerken_div:
            for dl in kenmerken_div.find_all("dl"):
                dt = dl.find("dt")
                dd = dl.find("dd")
                if dt and dd:
                    key = dt.get_text(strip=True)
                    val = dd.get_text(strip=True)
                    features[key] = val
                    # Check for Dutch text "Soort zaak" (business type) from the website
                    if "Soort zaak" in key:
                        venue_type = val
        return venue_type, features

    def _extract_tags(self, soup: BeautifulSoup) -> list[str]:
        """
        Extract all tags from the page-section-tags div.

        Args:
            soup: BeautifulSoup object containing the parsed HTML content.

        Returns:
            List of tag strings found on the page.
        """
        tags = []
        tags_div = soup.select_one(".page-section-tags")
        if tags_div:
            for tag_link in tags_div.find_all("a", class_="btn-tag-large"):
                tag_text = tag_link.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)
        return tags
