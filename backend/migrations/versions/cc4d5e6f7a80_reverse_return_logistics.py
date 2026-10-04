"""Add reverse-return logistics and supplier return destination."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "cc4d5e6f7a80"
down_revision = "c9e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "seller_verifications",
        sa.Column("return_address_line_1", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "seller_verifications",
        sa.Column("return_address_line_2", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "seller_verifications",
        sa.Column("return_landmark", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "seller_verifications",
        sa.Column("return_city", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "seller_verifications",
        sa.Column("return_state", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "seller_verifications",
        sa.Column("return_postal_code", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "seller_verifications",
        sa.Column(
            "return_country",
            sa.String(length=100),
            nullable=False,
            server_default="India",
        ),
    )
    op.alter_column("seller_verifications", "return_country", server_default=None)

    pickup_enum = postgresql.ENUM(
        "PENDING", "ASSIGNED", "PICKED_UP", name="pickupstatus", create_type=False
    )
    delivery_enum = postgresql.ENUM(
        "NOT_STARTED",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "FAILED",
        name="deliverystatus",
        create_type=False,
    )
    op.create_table(
        "return_delivery_assignments",
        sa.Column("return_request_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_id", sa.Integer(), nullable=True),
        sa.Column("agent_name", sa.String(length=150), nullable=True),
        sa.Column("agent_phone", sa.String(length=30), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("pickup_status", pickup_enum, nullable=False),
        sa.Column("pickup_time", sa.DateTime(), nullable=True),
        sa.Column("delivery_status", delivery_enum, nullable=False),
        sa.Column("out_for_delivery_time", sa.DateTime(), nullable=True),
        sa.Column("delivery_time", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_attempt_reason", sa.Text(), nullable=True),
        sa.Column("failed_reason", sa.Text(), nullable=True),
        sa.Column("next_action", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("supplier_name", sa.String(length=150), nullable=True),
        sa.Column("supplier_business_name", sa.String(length=255), nullable=True),
        sa.Column("supplier_phone", sa.String(length=30), nullable=True),
        sa.Column("supplier_address_line_1", sa.String(length=255), nullable=True),
        sa.Column("supplier_address_line_2", sa.String(length=255), nullable=True),
        sa.Column("supplier_landmark", sa.String(length=255), nullable=True),
        sa.Column("supplier_city", sa.String(length=100), nullable=True),
        sa.Column("supplier_state", sa.String(length=100), nullable=True),
        sa.Column("supplier_postal_code", sa.String(length=20), nullable=True),
        sa.Column("supplier_country", sa.String(length=100), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["return_request_id"], ["return_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("return_request_id"),
    )
    op.alter_column("return_delivery_assignments", "attempts", server_default=None)


def downgrade():
    op.drop_table("return_delivery_assignments")
    op.drop_column("seller_verifications", "return_country")
    op.drop_column("seller_verifications", "return_postal_code")
    op.drop_column("seller_verifications", "return_state")
    op.drop_column("seller_verifications", "return_city")
    op.drop_column("seller_verifications", "return_landmark")
    op.drop_column("seller_verifications", "return_address_line_2")
    op.drop_column("seller_verifications", "return_address_line_1")
