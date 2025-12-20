"""Venue model using SQLModel."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from cityvibe_core.models.base import TimestampMixin, UUIDMixin


class OpeningHours(SQLModel):
    """Structured daily hours for AI reasoning."""

    day: str  # "monday", "tuesday", etc.
    opens: str | None = None  # "08:00"
    closes: str | None = None  # "18:00"
    is_closed: bool = False


class VenueLink(SQLModel):
    """Deep links for tickets or reservations used by the AI Agent."""

    label: str  # "Tickets", "Reservation", "Menu", "Website"
    url: str


class VenueBase(SQLModel):
    """Base fields shared by all Venue variants."""

    name: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None)
    website_url: str = Field(unique=True, index=True)
    city: str = Field(default="Amsterdam", max_length=100, index=True)
    state: str | None = Field(default="Noord-Holland", max_length=50)
    country: str = Field(default="NL", max_length=50)

    latitude: float = Field(index=True)
    longitude: float = Field(index=True)

    venue_type: str | None = Field(default=None, max_length=50, index=True)
    price_range: str | None = Field(default=None)
    active: bool = Field(default=True, index=True)

    # Cleaned fields for the Agent
    tags: list[str] = Field(default=[], sa_column=Column(JSONB))
    opening_hours: list[OpeningHours] = Field(default=[], sa_column=Column(JSONB))
    external_links: list[VenueLink] = Field(default=[], sa_column=Column(JSONB))
    features: dict[str, Any] = Field(default={}, sa_column=Column(JSONB))


class Venue(VenueBase, UUIDMixin, TimestampMixin, table=True):
    """The physical table in the Neon Postgres DB."""

    # PostGIS Location Column (order is Lon, Lat)
    location: Any = Field(
        sa_column=Column(
            Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
            nullable=False
        )
    )
    scraper_config: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    last_scraped_at: datetime | None = Field(default=None, index=True)
    source: str = Field(default="debuik", index=True)


class VenueCreate(VenueBase):
    """Schema for creating venues (no id, timestamps)."""

    pass


class VenuePublic(VenueBase):
    """Schema for API responses and data transfer."""

    id: UUID
    created_at: datetime
    updated_at: datetime | None
    last_scraped_at: datetime | None
