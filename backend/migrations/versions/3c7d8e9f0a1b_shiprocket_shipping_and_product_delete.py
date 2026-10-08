"""Add Shiprocket shipping quote fields and allow permanent product deletion

Revision ID: 3c7d8e9f0a1b
Revises: 2b6f7a8c9d10
Create Date: 2026-10-08
"""

from alembic import op
import sqlalchemy as sa

revision = "3c7d8e9f0a1b"
down_revision = "2b6f7a8c9d10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "checkout_sessions",
        sa.Column(
            "shipping_charge",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "checkout_sessions",
        sa.Column("shipping_quote", sa.JSON(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "shipping_charge",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("orders", sa.Column("shipping_quote", sa.JSON(), nullable=True))
    op.add_column(
        "shipments",
        sa.Column("quoted_shipping_charge", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("quoted_courier_company_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("quoted_courier_name", sa.String(length=255), nullable=True),
    )
    op.alter_column(
        "order_items",
        "product_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "order_items",
        sa.Column("supplier_id_snapshot", sa.Integer(), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("sku_snapshot", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("shipping_weight_kg_snapshot", sa.Numeric(10, 3), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("shipping_length_cm_snapshot", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("shipping_width_cm_snapshot", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("shipping_height_cm_snapshot", sa.Numeric(10, 2), nullable=True),
    )
    op.create_index(
        "ix_order_items_supplier_id_snapshot",
        "order_items",
        ["supplier_id_snapshot"],
        unique=False,
    )
    op.execute(sa.text("""
            UPDATE order_items oi
               SET supplier_id_snapshot = p.seller_id,
                   sku_snapshot = COALESCE(
                       (SELECT pv.sku FROM product_variants pv WHERE pv.id = oi.variant_id),
                       p.sku
                   ),
                   shipping_weight_kg_snapshot = p.shipping_weight_kg,
                   shipping_length_cm_snapshot = p.shipping_length_cm,
                   shipping_width_cm_snapshot = p.shipping_width_cm,
                   shipping_height_cm_snapshot = p.shipping_height_cm
              FROM products p
             WHERE oi.product_id = p.id
            """))
    op.alter_column("checkout_sessions", "shipping_charge", server_default=None)
    op.alter_column("orders", "shipping_charge", server_default=None)


def downgrade():
    op.alter_column(
        "order_items",
        "product_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("shipments", "quoted_courier_name")
    op.drop_column("shipments", "quoted_courier_company_id")
    op.drop_index("ix_order_items_supplier_id_snapshot", table_name="order_items")
    op.drop_column("order_items", "shipping_height_cm_snapshot")
    op.drop_column("order_items", "shipping_width_cm_snapshot")
    op.drop_column("order_items", "shipping_length_cm_snapshot")
    op.drop_column("order_items", "shipping_weight_kg_snapshot")
    op.drop_column("order_items", "sku_snapshot")
    op.drop_column("order_items", "supplier_id_snapshot")
    op.drop_column("shipments", "quoted_shipping_charge")
    op.drop_column("orders", "shipping_quote")
    op.drop_column("orders", "shipping_charge")
    op.drop_column("checkout_sessions", "shipping_quote")
    op.drop_column("checkout_sessions", "shipping_charge")
