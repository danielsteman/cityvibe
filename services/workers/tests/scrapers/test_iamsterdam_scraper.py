"""Tests for Iamsterdam scraper."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup
from cityvibe_core.models.venue import VenueBase
from httpx import Response
from workers.scrapers.iamsterdam_scraper import IamsterdamScraper


class TestIamsterdamScraper:
    """Test cases for IamsterdamScraper."""

    @pytest.fixture
    def venue(self):
        """Create a test venue."""
        return VenueBase(
            name="Iamsterdam",
            website_url="https://www.iamsterdam.com/en/see-and-do/whats-on/events",
            city="Amsterdam",
            country="NL",
        )

    @pytest.fixture
    def scraper(self, venue):
        """Create a scraper instance."""
        return IamsterdamScraper(venue)

    @pytest.mark.asyncio
    async def test_get_sitemap_urls_filters_event_urls(self, scraper):
        """Test that _get_sitemap_urls filters for event/location URLs."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://www.iamsterdam.com/en/see-and-do/whats-on/calendar/event-1</loc>
            </url>
            <url>
                <loc>https://www.iamsterdam.com/en/see-and-do/whats-on/calendar/event-2</loc>
            </url>
            <url>
                <loc>https://www.iamsterdam.com/en/see-and-do/whats-on/calendar</loc>
            </url>
            <url>
                <loc>https://www.iamsterdam.com/en/other-page</loc>
            </url>
        </urlset>"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Response(
                status_code=200,
                content=sitemap_xml.encode(),
                request=MagicMock(),
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            urls = await scraper._get_sitemap_urls()

            # Should only include deep event URLs, not listing pages or other pages
            assert len(urls) == 2
            assert "event-1" in urls[0] or "event-1" in urls[1]
            assert "event-2" in urls[0] or "event-2" in urls[1]

    @pytest.mark.asyncio
    async def test_get_sitemap_urls_handles_empty_sitemap(self, scraper):
        """Test that _get_sitemap_urls handles empty sitemap gracefully."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        </urlset>"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Response(
                status_code=200,
                content=sitemap_xml.encode(),
                request=MagicMock(),
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            urls = await scraper._get_sitemap_urls()
            assert urls == []

    @pytest.mark.asyncio
    async def test_scrape_event_page_extracts_event_data(self, scraper):
        """Test that _scrape_event_page extracts event data from Next.js __NEXT_DATA__."""
        event_data = {
            "id": "event-123",
            "title": "Amsterdam Light Festival",
            "slug": "amsterdam-light-festival",
            "description": "Annual light art festival",
            "dates": {"start": "2024-12-01T18:00:00"},
        }

        next_data = {
            "props": {
                "pageProps": {
                    "pageType": "Event",
                    "event": event_data,
                }
            }
        }

        html = f'<html><body><script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script></body></html>'

        mock_response = Response(
            status_code=200,
            content=html.encode(),
            request=MagicMock(),
        )

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await scraper._scrape_event_page(
                mock_client_instance,
                "https://www.iamsterdam.com/en/events/amsterdam-light-festival",
            )

            assert result is not None
            assert result["kind"] == "Event"
            assert result["title"] == "Amsterdam Light Festival"
            assert result["description"] == "Annual light art festival"
            assert (
                result["source_url"]
                == "https://www.iamsterdam.com/en/events/amsterdam-light-festival"
            )

    @pytest.mark.asyncio
    async def test_scrape_event_page_extracts_location_data(self, scraper):
        """Test that _scrape_event_page extracts location data from Next.js __NEXT_DATA__."""
        location_data = {
            "id": "loc-456",
            "name": "AMAZE",
            "slug": "amaze",
            "description": "Interactive experience",
            "address": {
                "street": "Damrak",
                "city": "Amsterdam",
                "zipcode": "1012LG",
            },
            "coordinates": {
                "latitude": 52.3791,
                "longitude": 4.9003,
            },
        }

        next_data = {
            "props": {
                "pageProps": {
                    "pageType": "Location",
                    "Location": location_data,
                }
            }
        }

        html = f'<html><body><script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script></body></html>'

        mock_response = Response(
            status_code=200,
            content=html.encode(),
            request=MagicMock(),
        )

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await scraper._scrape_event_page(
                mock_client_instance, "https://www.iamsterdam.com/en/locations/amaze"
            )

            assert result is not None
            assert result["kind"] == "Location"
            assert result["title"] == "AMAZE"
            assert result["name"] == "AMAZE"
            assert result["description"] == "Interactive experience"
            assert result["address"]["city"] == "Amsterdam"

    @pytest.mark.asyncio
    async def test_scrape_event_page_handles_missing_next_data(self, scraper):
        """Test that _scrape_event_page returns None when __NEXT_DATA__ is missing."""
        html = "<html><body><h1>No Next.js data here</h1></body></html>"

        mock_response = Response(
            status_code=200,
            content=html.encode(),
            request=MagicMock(),
        )

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await scraper._scrape_event_page(
                mock_client_instance, "https://www.iamsterdam.com/en/some-page"
            )

            assert result is None

    def test_normalize_event(self, scraper):
        """Test that _normalize_event normalizes event data correctly."""
        event_data = {
            "id": "event-123",
            "slug": "test-event",
            "title": "Test Event",
            "description": "Event description",
            "dates": {"start": "2024-12-01T18:00:00"},
            "images": [{"src": "https://example.com/image.jpg"}],
        }

        page_props = {
            "directory": "events",
            "seo": {
                "title": "SEO Title",
                "description": "SEO Description",
            },
        }

        result = scraper._normalize_event(
            event_data, page_props, "https://www.iamsterdam.com/en/events/test-event"
        )

        assert result["kind"] == "Event"
        assert result["title"] == "Test Event"
        assert result["name"] == "Test Event"
        assert result["description"] == "Event description"
        assert result["seo_title"] == "SEO Title"
        assert result["main_image"] == "https://example.com/image.jpg"
        assert result["source_url"] == "https://www.iamsterdam.com/en/events/test-event"

    def test_normalize_location_as_event(self, scraper):
        """Test that _normalize_location_as_event normalizes location data correctly."""
        location_data = {
            "id": "loc-456",
            "ffID": "ff-789",
            "slug": "test-location",
            "name": "Test Location",
            "description": "Location description",
            "address": {
                "street": "Main Street",
                "houseNumber": "123",
                "city": "Amsterdam",
                "zipcode": "1000AA",
            },
            "coordinates": {
                "latitude": 52.3791,
                "longitude": 4.9003,
            },
            "images": [{"src": "https://example.com/location.jpg"}],
        }

        page_props = {
            "directory": "locations",
            "seo": {
                "title": "Location SEO Title",
            },
        }

        result = scraper._normalize_location_as_event(
            location_data,
            page_props,
            "https://www.iamsterdam.com/en/locations/test-location",
        )

        assert result["kind"] == "Location"
        assert result["title"] == "Test Location"
        assert result["name"] == "Test Location"
        assert result["description"] == "Location description"
        assert result["address"]["city"] == "Amsterdam"
        assert result["coordinates"]["lat"] == 52.3791
        assert result["coordinates"]["lng"] == 4.9003
        assert result["main_image"] == "https://example.com/location.jpg"
        assert result["source_url"] == "https://www.iamsterdam.com/en/locations/test-location"
