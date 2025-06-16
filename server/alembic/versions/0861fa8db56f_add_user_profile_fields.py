"""add_user_profile_fields

Revision ID: 0861fa8db56f
Revises: 5fb4d4ff1a45
Create Date: 2025-06-15 23:16:25.781861

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0861fa8db56f'
down_revision: Union[str, None] = '5fb4d4ff1a45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add profile fields to users table
    op.add_column('users', sa.Column('full_name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('settings', sa.Text(), nullable=True, server_default='{}'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove profile fields from users table
    op.drop_column('users', 'settings')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'bio')
    op.drop_column('users', 'full_name')
