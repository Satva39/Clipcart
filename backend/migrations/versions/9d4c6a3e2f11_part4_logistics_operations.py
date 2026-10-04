"""part 4 logistics operational fields

Revision ID: 9d4c6a3e2f11
Revises: f1b7c9d2e4aa
Create Date: 2026-09-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "9d4c6a3e2f11"
down_revision = ("f1b7c9d2e4aa", "52be80a63d03")
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "delivery_assignments",
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column("out_for_delivery_time", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column(
            "delivery_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column("last_attempt_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column("failed_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column("next_action", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column("customer_delivery_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column("proof_of_delivery_reference", sa.String(length=500), nullable=True),
    )
    op.alter_column("delivery_assignments", "delivery_attempts", server_default=None)


def downgrade():
    op.drop_column("delivery_assignments", "proof_of_delivery_reference")
    op.drop_column("delivery_assignments", "customer_delivery_notes")
    op.drop_column("delivery_assignments", "next_action")
    op.drop_column("delivery_assignments", "failed_reason")
    op.drop_column("delivery_assignments", "last_attempt_reason")
    op.drop_column("delivery_assignments", "last_attempt_at")
    op.drop_column("delivery_assignments", "delivery_attempts")
    op.drop_column("delivery_assignments", "out_for_delivery_time")
    op.drop_column("delivery_assignments", "assigned_at")
