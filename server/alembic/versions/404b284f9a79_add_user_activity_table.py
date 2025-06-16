"""add_user_activity_table

Revision ID: 404b284f9a79
Revises: 0861fa8db56f
Create Date: 2025-06-15 23:21:30.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "404b284f9a79"
down_revision: Union[str, None] = "0861fa8db56f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_activities table
    op.create_table(
        "user_activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("activity_description", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("activity_metadata", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(
        "idx_user_activities_user_created", "user_activities", ["user_id", "created_at"]
    )
    op.create_index("idx_user_activities_type", "user_activities", ["activity_type"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_user_activities_type", table_name="user_activities")
    op.drop_index("idx_user_activities_user_created", table_name="user_activities")

    # Drop table
    op.drop_table("user_activities")
