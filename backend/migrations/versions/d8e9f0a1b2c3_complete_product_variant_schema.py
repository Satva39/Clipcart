"""Complete product variant schema

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-09-30 14:05:00

Adds ProductVariant fields required by the current SQLAlchemy model:
- option_values
- compare_price
- is_active
Also widens value from 100 to 500 characters to match the model.
"""

from alembic import op
import sqlalchemy as sa

revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("product_variants", schema=None) as batch_op:
        batch_op.add_column(sa.Column("option_values", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("compare_price", sa.Numeric(10, 2), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.alter_column(
            "value",
            existing_type=sa.String(length=100),
            type_=sa.String(length=500),
            existing_nullable=False,
        )

    # Remove the temporary server default after existing rows have been backfilled.
    with op.batch_alter_table("product_variants", schema=None) as batch_op:
        batch_op.alter_column("is_active", server_default=None)


def downgrade():
    with op.batch_alter_table("product_variants", schema=None) as batch_op:
        batch_op.alter_column(
            "value",
            existing_type=sa.String(length=500),
            type_=sa.String(length=100),
            existing_nullable=False,
        )
        batch_op.drop_column("is_active")
        batch_op.drop_column("compare_price")
        batch_op.drop_column("option_values")
