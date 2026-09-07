"""add lookup indexes

Revision ID: 8f2c9c8d6b4a
Revises: 531f488dd601
Create Date: 2026-09-07 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f2c9c8d6b4a"
down_revision: str | Sequence[str] | None = "531f488dd601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_url_monitor_owner_user_id", "url_monitor", ["owner_user_id"])
    op.create_index("ix_url_monitor_owner_group_id", "url_monitor", ["owner_group_id"])
    op.create_index("ix_user_groups_group_id", "user_groups", ["group_id"])
    op.create_index("ix_group_admins_group_id", "group_admins", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_group_admins_group_id", table_name="group_admins")
    op.drop_index("ix_user_groups_group_id", table_name="user_groups")
    op.drop_index("ix_url_monitor_owner_group_id", table_name="url_monitor")
    op.drop_index("ix_url_monitor_owner_user_id", table_name="url_monitor")
