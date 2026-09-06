"""add groups schema

Revision ID: 531f488dd601
Revises: d928e7bdcea3
Create Date: 2026-09-06 13:01:19.358098

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "531f488dd601"
down_revision: str | Sequence[str] | None = "d928e7bdcea3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
