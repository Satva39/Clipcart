"""Add missing product JSON fields.

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
"""

from alembic import op
import sqlalchemy as sa

revision = "b6c7d8e9f0a1"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("highlights", sa.JSON(), nullable=True))
    op.add_column("products", sa.Column("specifications", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("products", "specifications")
    op.drop_column("products", "highlights")
