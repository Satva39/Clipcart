"""Merge conflicting branches

Revision ID: 121241a0d4d0
Revises: cc4d5e6f7a80, d1e2f3a4b5c6
Create Date: 2026-10-02 19:20:21.568169

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '121241a0d4d0'
down_revision = ('cc4d5e6f7a80', 'd1e2f3a4b5c6')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
