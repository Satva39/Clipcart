"""Add address coordinates and Shiprocket tracking/label fields.

Revision ID: f0a1b2c3d4e5
Revises: e4f5a6b7c8d9
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "f0a1b2c3d4e5"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade():
    for table, col in (("customer_addresses", "latitude"), ("customer_addresses", "longitude"),
                       ("seller_verifications", "return_latitude"), ("seller_verifications", "return_longitude"),
                       ("orders", "delivery_latitude"), ("orders", "delivery_longitude")):
        op.add_column(table, sa.Column(col, sa.Numeric(10, 7), nullable=True))

    op.add_column("shipments", sa.Column("label_url", sa.Text(), nullable=True))
    op.add_column("shipments", sa.Column("tracking_url", sa.Text(), nullable=True))
    op.add_column("shipments", sa.Column("estimated_delivery_at", sa.DateTime(), nullable=True))
    op.add_column("shipments", sa.Column("tracking_data", sa.JSON(), nullable=True))
    op.add_column("shipments", sa.Column("tracking_events", sa.JSON(), nullable=True))
    op.add_column("shipments", sa.Column("last_tracking_event_at", sa.DateTime(), nullable=True))


def downgrade():
    for col in ("last_tracking_event_at", "tracking_events", "tracking_data", "estimated_delivery_at", "tracking_url", "label_url"):
        op.drop_column("shipments", col)
    for table, col in (("orders", "delivery_longitude"), ("orders", "delivery_latitude"),
                       ("seller_verifications", "return_longitude"), ("seller_verifications", "return_latitude"),
                       ("customer_addresses", "longitude"), ("customer_addresses", "latitude")):
        op.drop_column(table, col)
