"""Add persistent reverse-logistics fields to return requests."""

from alembic import op
import sqlalchemy as sa

revision = "d1e2f3a4b5c6"
down_revision = "c9e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    columns = [
        ("logistics_agent_name", "VARCHAR(150)"),
        ("logistics_agent_phone", "VARCHAR(30)"),
        ("logistics_assigned_at", "TIMESTAMP"),
        ("customer_picked_up_at", "TIMESTAMP"),
        ("supplier_received_at", "TIMESTAMP"),
        ("logistics_notes", "TEXT"),
    ]
    for name, sql_type in columns:
        op.execute(
            f"ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS {name} {sql_type}"
        )
    op.execute("ALTER TABLE return_requests ALTER COLUMN status TYPE VARCHAR(50)")


def downgrade():
    for name in [
        "logistics_notes",
        "supplier_received_at",
        "customer_picked_up_at",
        "logistics_assigned_at",
        "logistics_agent_phone",
        "logistics_agent_name",
    ]:
        op.execute(f"ALTER TABLE return_requests DROP COLUMN IF EXISTS {name}")
    op.execute("ALTER TABLE return_requests ALTER COLUMN status TYPE VARCHAR(30)")
