"""added groups

Revision ID: d928e7bdcea3
Revises: e32878610dda
Create Date: 2026-09-06 12:53:51.035084

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d928e7bdcea3"
down_revision: str | Sequence[str] | None = "e32878610dda"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
