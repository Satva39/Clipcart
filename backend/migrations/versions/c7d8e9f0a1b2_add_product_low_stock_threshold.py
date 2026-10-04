"""Add missing product low-stock threshold.

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
"""

from alembic import op
import sqlalchemy as sa

revision = "c7d8e9f0a1b2"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column(
            "low_stock_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
    )
    # Keep database behavior aligned with the SQLAlchemy model, which owns the
    # Python-side default rather than a permanent database-side default.
    op.alter_column("products", "low_stock_threshold", server_default=None)


def downgrade():
    op.drop_column("products", "low_stock_threshold")
