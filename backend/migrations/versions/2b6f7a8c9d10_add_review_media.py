"""Add media attachments to customer reviews

Revision ID: 2b6f7a8c9d10
Revises: f0a1b2c3d4e5
Create Date: 2026-10-07
"""

from alembic import op
import sqlalchemy as sa

revision = "2b6f7a8c9d10"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_media",
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("media_url", sa.Text(), nullable=False),
        sa.Column("public_id", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_review_media_review_id", "review_media", ["review_id"], unique=False
    )


def downgrade():
    op.drop_index("ix_review_media_review_id", table_name="review_media")
    op.drop_table("review_media")
