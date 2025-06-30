"""add_email_events_tables

Revision ID: 589f0c1e2a43
Revises: 404b284f9a79
Create Date: 2025-06-30 00:09:07.796958

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "589f0c1e2a43"
down_revision: Union[str, None] = "404b284f9a79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum type for bounce types
    bounce_type_enum = sa.Enum("permanent", "transient", "undetermined", name="bouncetype")
    bounce_type_enum.create(op.get_bind(), checkfirst=True)

    # Create email_bounces table
    op.create_table(
        "email_bounces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("bounce_type", bounce_type_enum, nullable=False),
        sa.Column("bounce_subtype", sa.String(length=50), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("feedback_id", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("diagnostic_code", sa.Text(), nullable=True),
        sa.Column("reporting_mta", sa.String(length=255), nullable=True),
        sa.Column("suppressed", sa.Boolean(), nullable=True, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feedback_id"),
    )
    op.create_index(op.f("ix_email_bounces_email"), "email_bounces", ["email"], unique=False)

    # Create email_complaints table
    op.create_table(
        "email_complaints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("complaint_type", sa.String(length=50), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("feedback_id", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("suppressed", sa.Boolean(), nullable=True, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feedback_id"),
    )
    op.create_index(op.f("ix_email_complaints_email"), "email_complaints", ["email"], unique=False)

    # Create email_suppressions table
    op.create_table(
        "email_suppressions",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("email"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables
    op.drop_table("email_suppressions")
    op.drop_index(op.f("ix_email_complaints_email"), table_name="email_complaints")
    op.drop_table("email_complaints")
    op.drop_index(op.f("ix_email_bounces_email"), table_name="email_bounces")
    op.drop_table("email_bounces")

    # Drop enum type
    bounce_type_enum = sa.Enum("permanent", "transient", "undetermined", name="bouncetype")
    bounce_type_enum.drop(op.get_bind(), checkfirst=True)
