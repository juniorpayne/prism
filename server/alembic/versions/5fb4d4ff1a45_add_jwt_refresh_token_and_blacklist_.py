"""Add JWT refresh token and blacklist tables

Revision ID: 5fb4d4ff1a45
Revises: f2bd7eaed5ce
Create Date: 2025-06-12 21:38:18.465280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '5fb4d4ff1a45'
down_revision: Union[str, None] = 'f2bd7eaed5ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create token_blacklist table
    op.create_table(
        "token_blacklist",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("jti", sa.String(length=255), nullable=False),
        sa.Column("token_type", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blacklisted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index(op.f("ix_token_blacklist_jti"), "token_blacklist", ["jti"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop token_blacklist table
    op.drop_index(op.f("ix_token_blacklist_jti"), table_name="token_blacklist")
    op.drop_table("token_blacklist")
