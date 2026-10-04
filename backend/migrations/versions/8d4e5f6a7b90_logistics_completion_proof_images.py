"""Store Cloudinary completion photos for forward and reverse logistics."""

from alembic import op
import sqlalchemy as sa

revision = "8d4e5f6a7b90"
down_revision = "7c3e9b1a2d44"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "delivery_assignments",
        sa.Column("proof_of_delivery_image_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "delivery_assignments",
        sa.Column(
            "proof_of_delivery_image_public_id", sa.String(length=255), nullable=True
        ),
    )
    op.add_column(
        "return_requests",
        sa.Column("completion_image_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "return_requests",
        sa.Column("completion_image_public_id", sa.String(length=255), nullable=True),
    )


def downgrade():
    op.drop_column("return_requests", "completion_image_public_id")
    op.drop_column("return_requests", "completion_image_url")
    op.drop_column("delivery_assignments", "proof_of_delivery_image_public_id")
    op.drop_column("delivery_assignments", "proof_of_delivery_image_url")
