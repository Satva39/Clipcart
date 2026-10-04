"""Shiprocket delivery integration and shipping package metadata.

Revision ID: e4f5a6b7c8d9
Revises: 8d4e5f6a7b90
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c8d9"
down_revision = "8d4e5f6a7b90"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column("shipping_weight_kg", sa.Numeric(10, 3), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("shipping_length_cm", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("shipping_width_cm", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("shipping_height_cm", sa.Numeric(10, 2), nullable=True),
    )

    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("shiprocket_reference_id", sa.String(length=50), nullable=False),
        sa.Column("shiprocket_order_id", sa.Integer(), nullable=True),
        sa.Column("shiprocket_shipment_id", sa.Integer(), nullable=True),
        sa.Column("awb_code", sa.String(length=128), nullable=True),
        sa.Column("courier_company_id", sa.Integer(), nullable=True),
        sa.Column("courier_name", sa.String(length=255), nullable=True),
        sa.Column("pickup_location_id", sa.String(length=64), nullable=True),
        sa.Column("pickup_location", sa.String(length=100), nullable=True),
        sa.Column(
            "status", sa.String(length=80), nullable=False, server_default="PENDING"
        ),
        sa.Column("status_id", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_webhook_at", sa.DateTime(), nullable=True),
        sa.Column("last_webhook_hash", sa.String(length=64), nullable=True),
        sa.Column("pickup_scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("awb_assigned_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "order_id", "supplier_id", name="uq_shipments_order_supplier"
        ),
        sa.UniqueConstraint(
            "shiprocket_reference_id", name="uq_shipments_shiprocket_reference"
        ),
    )
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"])
    op.create_index("ix_shipments_supplier_id", "shipments", ["supplier_id"])
    op.create_index(
        "ix_shipments_shiprocket_order_id", "shipments", ["shiprocket_order_id"]
    )
    op.create_index(
        "ix_shipments_shiprocket_shipment_id",
        "shipments",
        ["shiprocket_shipment_id"],
    )
    op.create_index("ix_shipments_awb_code", "shipments", ["awb_code"])
    op.create_index("ix_shipments_status", "shipments", ["status"])
    op.create_index(
        "ix_shipments_shiprocket_reference_id",
        "shipments",
        ["shiprocket_reference_id"],
    )


def downgrade():
    for index_name in (
        "ix_shipments_shiprocket_reference_id",
        "ix_shipments_status",
        "ix_shipments_awb_code",
        "ix_shipments_shiprocket_shipment_id",
        "ix_shipments_shiprocket_order_id",
        "ix_shipments_supplier_id",
        "ix_shipments_order_id",
    ):
        op.drop_index(index_name, table_name="shipments")
    op.drop_table("shipments")
    for column in (
        "shipping_height_cm",
        "shipping_width_cm",
        "shipping_length_cm",
        "shipping_weight_kg",
    ):
        op.drop_column("products", column)
