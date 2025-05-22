"""add updated_at to users

Revision ID: add_updated_at_to_users
Revises: 05e6fdec17d1
Create Date: 2024-03-22 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_updated_at_to_users'
down_revision = '05e6fdec17d1'
branch_labels = None
depends_on = None


def upgrade():
    # Add updated_at column with timezone support
    op.add_column('users',
        sa.Column('updated_at', 
                  postgresql.TIMESTAMP(timezone=True), 
                  server_default=sa.text('now()'),
                  nullable=False)
    )


def downgrade():
    # Remove updated_at column
    op.drop_column('users', 'updated_at') 