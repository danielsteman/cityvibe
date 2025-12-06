"""Tests for Filmladder scraper."""

import pytest
from cityvibe_core.models.venue import VenueBase
from workers.scrapers.filmladder_scraper import FilmladderScraper


class TestFilmladderScraper:
    """Test cases for FilmladderScraper."""

    @pytest.mark.asyncio
    async def test_parse_html_returns_empty_list_for_empty_html(self):
        """Test that _parse_html returns empty list for empty HTML."""
        # Create a venue using VenueBase schema
        venue = VenueBase(
            name="Test Venue",
            website_url="https://www.filmladder.nl/amsterdam/bioscopen",
            city="Amsterdam",
        )

        scraper = FilmladderScraper(venue)

        # Test with empty HTML
        result = await scraper._parse_html("", "https://www.filmladder.nl/amsterdam/bioscopen")

        assert result == []

    @pytest.mark.asyncio
    async def test_parse_html_extracts_events_from_cinema_structure(self):
        """Test that _parse_html extracts events from cinema-grouped HTML structure."""
        venue = VenueBase(
            name="Test Cinema",
            website_url="https://www.filmladder.nl/amsterdam/bioscopen",
            city="Amsterdam",
        )

        scraper = FilmladderScraper(venue)

        # Sample HTML with cinema structure
        html = """
        <div class="cinema">
            <h2 class="cinema-name">Test Cinema</h2>
            <div class="film">
                <h3 class="title">The Matrix</h3>
                <time class="showtime" datetime="2024-12-03T20:00:00">20:00</time>
                <a href="/film/the-matrix">More info</a>
                <p class="description">A computer hacker learns about the true nature of reality</p>
            </div>
            <div class="film">
                <h3 class="title">Inception</h3>
                <time class="showtime" datetime="2024-12-03T22:30:00">22:30</time>
                <a href="/film/inception">More info</a>
            </div>
        </div>
        """

        result = await scraper._parse_html(html, "https://www.filmladder.nl")

        assert len(result) == 2
        assert result[0]["title"] == "The Matrix"
        assert result[0]["venue_name"] == "Test Cinema"
        assert result[0]["start_time"] == "2024-12-03T20:00:00"
        assert (
            result[0]["description"] == "A computer hacker learns about the true nature of reality"
        )
        assert "the-matrix" in result[0]["source_url"]

        assert result[1]["title"] == "Inception"
        assert result[1]["start_time"] == "2024-12-03T22:30:00"

    @pytest.mark.asyncio
    async def test_parse_html_extracts_events_from_flat_structure(self):
        """Test that _parse_html extracts events from flat HTML structure."""
        venue = VenueBase(
            name="Test Cinema",
            website_url="https://www.filmladder.nl/amsterdam/bioscopen",
            city="Amsterdam",
        )

        scraper = FilmladderScraper(venue)

        # Sample HTML with flat structure (no cinema grouping)
        html = """
        <div class="film">
            <h3 class="title">Interstellar</h3>
            <time class="showtime">19:00</time>
            <a href="/film/interstellar">Details</a>
        </div>
        <div class="movie">
            <h4 class="title">Dune</h4>
            <span class="time">21:30</span>
            <a href="/film/dune">Details</a>
        </div>
        """

        result = await scraper._parse_html(html, "https://www.filmladder.nl")

        assert len(result) == 2
        assert result[0]["title"] == "Interstellar"
        assert result[0]["venue_name"] == "Test Cinema"
        assert result[1]["title"] == "Dune"
