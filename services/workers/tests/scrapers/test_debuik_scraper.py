"""Tests for Debuik scraper."""

import pytest
from cityvibe_core.models.venue import VenueBase
from workers.scrapers.debuik_batch_scraper import DebuikScraper


class TestDebuikScraper:
    """Test cases for DebuikScraper."""

    @pytest.fixture
    def venue(self):
        """Create a test venue."""
        return VenueBase(
            name="Test Restaurant",
            website_url="https://www.debuik.nl/amsterdam/restaurant/test-restaurant",
            city="Amsterdam",
        )

    @pytest.fixture
    def scraper(self, venue):
        """Create a scraper instance."""
        return DebuikScraper(venue)

    @pytest.mark.asyncio
    async def test_parse_html_returns_none_for_empty_html(self, scraper):
        """Test that _parse_html returns None for empty HTML."""
        result = await scraper._parse_html("", "https://www.debuik.nl/amsterdam/restaurant/test")

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_html_returns_none_when_name_missing(self, scraper):
        """Test that _parse_html returns None when venue name cannot be extracted."""
        html = """
        <html>
            <body>
                <div class="address">
                    <span class="street">Test Street 123</span>
                </div>
            </body>
        </html>
        """

        result = await scraper._parse_html(html, "https://www.debuik.nl/amsterdam/restaurant/test")

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_html_extracts_complete_venue_data(self, scraper):
        """Test that _parse_html extracts all venue data correctly."""
        html = """
        <html>
            <body>
                <div class="address">
                    <h1>Test Restaurant</h1>
                    <span class="street">Vijzelstraat 93</span>
                    <span class="postcode">1017 HA</span>
                    <span class="city">Amsterdam</span>
                </div>
                <div class="introductie">
                    <p>This is a test restaurant description.</p>
                </div>
                <div class="restaurant-slideshow">
                    <div class="restaurant-slide">
                        <img class="imgfade-transition" src="https://example.com/image.jpg" />
                    </div>
                </div>
                <div class="locatie-small">
                    <img src="https://maps.googleapis.com/maps/api/staticmap?center=52.3633362,4.8924013" />
                </div>
                <div class="openingstijden-tabel">
                    <div class="openingstijden-tabel-tr">
                        <div class="openingstijden-label">
                            <div>Maandag</div>
                        </div>
                        <div class="openingstijden-data">
                            <div class="openingstijden-gesloten">Gesloten</div>
                        </div>
                    </div>
                    <div class="openingstijden-tabel-tr">
                        <div class="openingstijden-label">
                            <div>Dinsdag</div>
                        </div>
                        <div class="openingstijden-data">
                            <div class="openingstijden-restaurant">
                                <span class="start">08:00</span>
                                <span class="einde">18:00</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="kenmerken">
                    <div class="content">
                        <dl>
                            <dt>Soort zaak</dt>
                            <dd>Restaurant</dd>
                            <dt>Keuken</dt>
                            <dd>Mediterraan</dd>
                        </dl>
                    </div>
                </div>
                <div class="restaurant-contactvlak">
                    <a href="https://external-website.com">Website</a>
                </div>
            </body>
        </html>
        """

        result = await scraper._parse_html(html, "https://www.debuik.nl/amsterdam/restaurant/test")

        assert result is not None
        assert result["name"] == "Test Restaurant"
        assert result["website_url"] == "https://external-website.com"
        assert result["city"] == "Amsterdam"
        assert result["state"] == "Noord-Holland"
        assert result["country"] == "NL"
        assert result["venue_type"] == "Restaurant"
        assert result["latitude"] is not None
        assert result["longitude"] is not None
        assert result["active"] is True

        # Check scraper_config
        config = result["scraper_config"]
        assert config["source"] == "debuik.nl"
        assert config["original_url"] == "https://www.debuik.nl/amsterdam/restaurant/test"
        assert config["street"] == "Vijzelstraat 93"
        assert config["zip_code"] == "1017 HA"
        assert config["description"] == "This is a test restaurant description."
        assert config["image_url"] == "https://example.com/image.jpg"
        assert "opening_hours" in config
        assert config["opening_hours"]["Maandag"] == "Gesloten"
        assert config["opening_hours"]["Dinsdag"] == "08:00 - 18:00"
        assert "features" in config
        assert config["features"]["Soort zaak"] == "Restaurant"
        assert config["features"]["Keuken"] == "Mediterraan"

    @pytest.mark.asyncio
    async def test_parse_html_uses_fallback_url_when_no_external_website(self, scraper):
        """Test that _parse_html uses original URL when no external website is found."""
        html = """
        <html>
            <body>
                <div class="address">
                    <h1>Test Restaurant</h1>
                </div>
            </body>
        </html>
        """

        result = await scraper._parse_html(html, "https://www.debuik.nl/amsterdam/restaurant/test")

        assert result is not None
        assert result["website_url"] == "https://www.debuik.nl/amsterdam/restaurant/test"

    def test_extract_address_info_from_address_div(self, scraper):
        """Test that _extract_address_info extracts data from .address div."""
        html = """
        <div class="address">
            <h1>Restaurant Name</h1>
            <span class="street">Main Street 123</span>
            <span class="postcode">1000 AA</span>
            <span class="city">Amsterdam</span>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_address_info(soup)

        assert result["name"] == "Restaurant Name"
        assert result["street"] == "Main Street 123"
        assert result["zip_code"] == "1000 AA"
        assert result["city"] == "Amsterdam"

    def test_extract_address_info_fallback_to_h1(self, scraper):
        """Test that _extract_address_info falls back to H1 when .address div is missing."""
        html = """
        <html>
            <body>
                <h1>Restaurant Name</h1>
            </body>
        </html>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_address_info(soup)

        assert result["name"] == "Restaurant Name"
        assert result["city"] == "Amsterdam"  # Default value

    def test_extract_description(self, scraper):
        """Test that _extract_description extracts description from .introductie."""
        html = """
        <div class="introductie">
            <p>This is a restaurant description with multiple sentences.</p>
            <p>It can have multiple paragraphs.</p>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_description(soup)

        assert result is not None
        assert "This is a restaurant description" in result
        assert "multiple paragraphs" in result

    def test_extract_description_returns_none_when_missing(self, scraper):
        """Test that _extract_description returns None when .introductie is missing."""
        html = "<html><body></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_description(soup)

        assert result is None

    def test_extract_image_from_slideshow(self, scraper):
        """Test that _extract_image extracts image from slideshow."""
        html = """
        <div class="restaurant-slideshow">
            <div class="restaurant-slide">
                <img class="imgfade-transition" src="https://example.com/slideshow.jpg" />
            </div>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_image(soup)

        assert result == "https://example.com/slideshow.jpg"

    def test_extract_image_fallback_to_thumbnails(self, scraper):
        """Test that _extract_image falls back to thumbnails when slideshow is missing."""
        html = """
        <div class="thumbnails">
            <img src="https://example.com/thumbnail.jpg" />
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_image(soup)

        assert result == "https://example.com/thumbnail.jpg"

    def test_extract_image_returns_none_when_missing(self, scraper):
        """Test that _extract_image returns None when no image is found."""
        html = "<html><body></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_image(soup)

        assert result is None

    def test_extract_lat_lon_from_map_image(self, scraper):
        """Test that _extract_lat_lon extracts coordinates from map image."""
        html = """
        <div class="locatie-small">
            <img src="https://maps.googleapis.com/maps/api/staticmap?center=52.3633362,4.8924013&zoom=15" />
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        lat, lon = scraper._extract_lat_lon(soup)

        assert lat is not None
        assert lon is not None
        assert str(lat) == "52.3633362"
        assert str(lon) == "4.8924013"

    def test_extract_lat_lon_from_style_attribute(self, scraper):
        """Test that _extract_lat_lon extracts coordinates from style attribute."""
        html = """
        <div class="locatie-large">
            <a style="background-image: url('https://maps.googleapis.com/maps/api/staticmap?center=52.3791,4.9003')"></a>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        lat, lon = scraper._extract_lat_lon(soup)

        assert lat is not None
        assert lon is not None
        assert str(lat) == "52.3791"
        assert str(lon) == "4.9003"

    def test_extract_lat_lon_returns_none_when_missing(self, scraper):
        """Test that _extract_lat_lon returns None when coordinates cannot be found."""
        html = "<html><body></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        lat, lon = scraper._extract_lat_lon(soup)

        assert lat is None
        assert lon is None

    def test_extract_opening_hours(self, scraper):
        """Test that _extract_opening_hours extracts opening hours correctly."""
        html = """
        <div class="openingstijden-tabel">
            <div class="openingstijden-tabel-tr">
                <div class="openingstijden-label">
                    <div>Maandag</div>
                </div>
                <div class="openingstijden-data">
                    <div class="openingstijden-gesloten">Gesloten</div>
                </div>
            </div>
            <div class="openingstijden-tabel-tr">
                <div class="openingstijden-label">
                    <div>Dinsdag</div>
                </div>
                <div class="openingstijden-data">
                    <div class="openingstijden-restaurant">
                        <span class="start">09:00</span>
                        <span class="einde">17:00</span>
                    </div>
                </div>
            </div>
            <div class="openingstijden-tabel-tr">
                <div class="openingstijden-label">
                    <div>Woensdag</div>
                </div>
                <div class="openingstijden-data">
                    <div class="openingstijden-restaurant">
                        <span class="start">10:00</span>
                        <span class="einde">18:00</span>
                    </div>
                </div>
            </div>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_opening_hours(soup)

        assert result["Maandag"] == "Gesloten"
        assert result["Dinsdag"] == "09:00 - 17:00"
        assert result["Woensdag"] == "10:00 - 18:00"

    def test_extract_opening_hours_returns_empty_when_missing(self, scraper):
        """Test that _extract_opening_hours returns empty dict when table is missing."""
        html = "<html><body></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        result = scraper._extract_opening_hours(soup)

        assert result == {}

    def test_extract_venue_features(self, scraper):
        """Test that _extract_venue_features extracts venue type and features."""
        html = """
        <div class="kenmerken">
            <div class="content">
                <dl>
                    <dt>Soort zaak</dt>
                    <dd>Restaurant</dd>
                    <dt>Keuken</dt>
                    <dd>Mediterraan</dd>
                    <dt>Prijs</dt>
                    <dd>€€</dd>
                </dl>
            </div>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        venue_type, features = scraper._extract_venue_features(soup)

        assert venue_type == "Restaurant"
        assert features["Soort zaak"] == "Restaurant"
        assert features["Keuken"] == "Mediterraan"
        assert features["Prijs"] == "€€"

    def test_extract_venue_features_defaults_to_restaurant(self, scraper):
        """Test that _extract_venue_features defaults to 'Restaurant' when type is missing."""
        html = """
        <div class="kenmerken">
            <div class="content">
                <dl>
                    <dt>Keuken</dt>
                    <dd>Mediterraan</dd>
                </dl>
            </div>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        venue_type, features = scraper._extract_venue_features(soup)

        assert venue_type == "Restaurant"
        assert features["Keuken"] == "Mediterraan"

    def test_extract_venue_features_returns_empty_when_missing(self, scraper):
        """Test that _extract_venue_features returns defaults when features are missing."""
        html = "<html><body></body></html>"
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        venue_type, features = scraper._extract_venue_features(soup)

        assert venue_type == "Restaurant"
        assert features == {}
