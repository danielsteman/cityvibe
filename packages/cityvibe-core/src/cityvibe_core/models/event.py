"""Event model using SQLModel."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel


class EventBase(SQLModel):
    """Base fields shared by all Event variants."""

    name: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None)
    start_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    end_date: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
    )
    venue_id: UUID = Field(foreign_key="venue.id", index=True)


class Event(EventBase, table=True):
    """The physical table in the Neon Postgres DB."""

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )


class EventCreate(EventBase):
    """Schema for creating events (no id, timestamps)."""

    pass


class EventPublic(EventBase):
    """Schema for API responses and data transfer."""

    id: UUID
    created_at: datetime
    updated_at: datetime | None
