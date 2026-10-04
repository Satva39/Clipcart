"""add logistics manager role

Revision ID: 52be80a63d03
Revises: c7ee5919ed8a
Create Date: 2026-08-26 00:05:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '52be80a63d03'
down_revision = 'c7ee5919ed8a'
branch_labels = None
depends_on = None


def upgrade():
    # Postgres enum types require a new value to be added
    # explicitly. This must run outside a transaction block
    # on Postgres < 12 — if this fails on your setup, run
    # the ALTER TYPE statement manually via psql instead.
    op.execute(
        "ALTER TYPE userrole ADD VALUE IF NOT EXISTS "
        "'LOGISTICS_MANAGER'"
    )


def downgrade():
    # Postgres does not support removing a value from an
    # enum type. Downgrading this migration is a no-op;
    # if you truly need to remove the value, it requires
    # recreating the enum type and re-pointing every
    # column that uses it.
    pass
