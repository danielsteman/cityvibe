"""Venue model using SQLModel."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from cityvibe_core.models.base import TimestampMixin, UUIDMixin


class VenueBase(SQLModel):
    """Base fields shared by all Venue variants."""

    name: str = Field(max_length=255, index=True)
    website_url: str = Field(unique=True, index=True)
    city: str = Field(max_length=100, index=True)
    state: str | None = Field(default=None, max_length=50)
    country: str = Field(default="US", max_length=50)
    latitude: Decimal | None = Field(default=None, max_digits=10, decimal_places=8)
    longitude: Decimal | None = Field(default=None, max_digits=11, decimal_places=8)
    venue_type: str | None = Field(default=None, max_length=50)
    scraper_config: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    active: bool = Field(default=True)


class Venue(VenueBase, UUIDMixin, TimestampMixin, table=True):  # type: ignore
    """Database table model for venues."""

    last_scraped_at: datetime | None = Field(default=None)


class VenueCreate(VenueBase):
    """Schema for creating venues (no id, timestamps)."""

    pass


class VenuePublic(VenueBase):
    """Schema for API responses and data transfer."""

    id: UUID
    created_at: datetime
    updated_at: datetime | None
    last_scraped_at: datetime | None
