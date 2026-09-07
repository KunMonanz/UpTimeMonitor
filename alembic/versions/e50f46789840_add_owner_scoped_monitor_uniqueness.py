"""Add owner scoped monitor uniqueness

Revision ID: e50f46789840
Revises: 8f2c9c8d6b4a
Create Date: 2026-09-07 10:26:56.435041

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e50f46789840"
down_revision: Union[str, Sequence[str], None] = "8f2c9c8d6b4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("url_monitor", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_url_monitor_owner_group_url",
            ["owner_group_id", "url"],
        )
        batch_op.create_unique_constraint(
            "uq_url_monitor_owner_user_url",
            ["owner_user_id", "url"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("url_monitor", schema=None) as batch_op:
        batch_op.drop_constraint("uq_url_monitor_owner_user_url", type_="unique")
        batch_op.drop_constraint("uq_url_monitor_owner_group_url", type_="unique")
