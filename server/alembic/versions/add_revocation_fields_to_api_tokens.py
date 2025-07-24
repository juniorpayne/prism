"""add revocation fields to api tokens

Revision ID: a1b2c3d4e5f6
Revises: f451eff9e401
Create Date: 2025-07-22 21:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f451eff9e401'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add revocation tracking columns to api_tokens table
    with op.batch_alter_table('api_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('revoked_by', 
            postgresql.UUID(as_uuid=True) if op.get_context().dialect.name == 'postgresql' else sa.String(36),
            nullable=True))


def downgrade() -> None:
    # Remove revocation tracking columns
    with op.batch_alter_table('api_tokens', schema=None) as batch_op:
        batch_op.drop_column('revoked_by')
        batch_op.drop_column('revoked_at')