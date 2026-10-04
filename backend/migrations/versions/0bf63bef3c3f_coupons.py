"""coupons

Revision ID: 0bf63bef3c3f
Revises: 11d2ec55905f
Create Date: 2026-08-06 12:54:02.375158

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0bf63bef3c3f'
down_revision = '11d2ec55905f'
branch_labels = None
depends_on = None


def upgrade():
    # Create PostgreSQL Enum first
    discount_type = postgresql.ENUM(
        "PERCENTAGE",
        "FIXED",
        name="discounttype",
    )
    discount_type.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("coupons", schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                "seller_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "minimum_order",
                sa.Numeric(10, 2),
                nullable=False,
                server_default="0",
            )
        )

        batch_op.alter_column(
            "discount_type",
            existing_type=sa.VARCHAR(length=20),
            type_=discount_type,
            postgresql_using="discount_type::discounttype",
            existing_nullable=False,
        )

        batch_op.alter_column(
            "usage_limit",
            existing_type=sa.INTEGER(),
            nullable=False,
        )

        batch_op.alter_column(
            "expires_at",
            existing_type=postgresql.TIMESTAMP(),
            nullable=True,
        )

        batch_op.create_foreign_key(
            None,
            "accounts",
            ["seller_id"],
            ["id"],
        )

        batch_op.drop_column("minimum_order_amount")
        batch_op.drop_column("description")
        batch_op.drop_column("starts_at")

    # ### end Alembic commands ###


def downgrade():

    with op.batch_alter_table("coupons", schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                "starts_at",
                postgresql.TIMESTAMP(),
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "description",
                sa.String(255),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "minimum_order_amount",
                sa.Numeric(10, 2),
                nullable=False,
            )
        )

        batch_op.drop_constraint(None, type_="foreignkey")

        batch_op.alter_column(
            "expires_at",
            existing_type=postgresql.TIMESTAMP(),
            nullable=False,
        )

        batch_op.alter_column(
            "usage_limit",
            existing_type=sa.INTEGER(),
            nullable=True,
        )

        batch_op.alter_column(
            "discount_type",
            existing_type=postgresql.ENUM(
                "PERCENTAGE",
                "FIXED",
                name="discounttype",
            ),
            type_=sa.VARCHAR(20),
            postgresql_using="discount_type::text",
            existing_nullable=False,
        )

        batch_op.drop_column("minimum_order")
        batch_op.drop_column("seller_id")

    postgresql.ENUM(
        "PERCENTAGE",
        "FIXED",
        name="discounttype",
    ).drop(op.get_bind(), checkfirst=True)

    # ### end Alembic commands ###
