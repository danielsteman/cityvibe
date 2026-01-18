"""Add vibe_embedding column to venue table

Revision ID: 8bd9068251d2
Revises: e2ac96fa9e3e
Create Date: 2026-01-10 16:00:00.000000

"""

from collections.abc import Sequence

from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8bd9068251d2"
down_revision: str | None = "e2ac96fa9e3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Ensure pgvector extension is enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add vibe_embedding column to venue table
    op.add_column(
        "venue",
        sa.Column(
            "vibe_embedding",
            Vector(1024),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Remove vibe_embedding column
    op.drop_column("venue", "vibe_embedding")
