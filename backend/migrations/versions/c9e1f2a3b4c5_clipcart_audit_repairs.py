"""Clipcart audit repairs: banner placement."""

from alembic import op

revision = "c9e1f2a3b4c5"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade():
    # The live project may already contain this column from a partial/manual
    # schema update. Keep the migration idempotent so `flask db upgrade`
    # cannot fail merely because the column/index already exists.
    op.execute(
        "ALTER TABLE admin_banners "
        "ADD COLUMN IF NOT EXISTS placement VARCHAR(50) "
        "NOT NULL DEFAULT 'HOME_HERO'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_admin_banners_placement "
        "ON admin_banners (placement)"
    )
    op.execute("ALTER TABLE admin_banners ALTER COLUMN placement DROP DEFAULT")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_admin_banners_placement")
    op.execute("ALTER TABLE admin_banners DROP COLUMN IF EXISTS placement")
