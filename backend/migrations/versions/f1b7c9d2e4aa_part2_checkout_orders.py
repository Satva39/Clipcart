"""Complete Clipcart Part 2 checkout, payments and customer orders.

Revision ID: f1b7c9d2e4aa
Revises: c7ee5919ed8a
Create Date: 2026-09-29

"""

from alembic import op
import sqlalchemy as sa

revision = "f1b7c9d2e4aa"
down_revision = "c7ee5919ed8a"
branch_labels = None
depends_on = None


def upgrade():
    # Existing OrderStatus enum is extended without recreating the type.
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'OUT_FOR_DELIVERY'")

    with op.batch_alter_table("order_items") as batch:
        batch.add_column(
            sa.Column("product_name_snapshot", sa.String(255), nullable=True)
        )
        batch.add_column(
            sa.Column("variant_name_snapshot", sa.String(100), nullable=True)
        )
        batch.add_column(
            sa.Column("variant_value_snapshot", sa.String(255), nullable=True)
        )
    op.execute(
        "UPDATE order_items SET product_name_snapshot = COALESCE((SELECT name FROM products WHERE products.id = order_items.product_id), '') WHERE product_name_snapshot IS NULL"
    )
    op.execute(
        "UPDATE order_items SET variant_name_snapshot = (SELECT name FROM product_variants WHERE product_variants.id = order_items.variant_id), variant_value_snapshot = (SELECT value FROM product_variants WHERE product_variants.id = order_items.variant_id) WHERE variant_id IS NOT NULL"
    )
    with op.batch_alter_table("order_items") as batch:
        batch.alter_column(
            "product_name_snapshot", nullable=False, existing_type=sa.String(255)
        )

    # Add the new columns first. Existing checkout sessions predate
    # idempotency_key, so the column must be backfilled before it becomes NOT NULL.
    with op.batch_alter_table("checkout_sessions") as batch:
        batch.add_column(sa.Column("order_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "taxable_base", sa.Numeric(12, 2), nullable=False, server_default="0"
            )
        )
        batch.add_column(
            sa.Column(
                "marketing_fee", sa.Numeric(12, 2), nullable=False, server_default="0"
            )
        )
        batch.add_column(
            sa.Column("tax", sa.Numeric(12, 2), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("idempotency_key", sa.String(80), nullable=True))
        batch.add_column(sa.Column("payment_error", sa.String(500), nullable=True))

    # Existing rows have no idempotency key because this column is new in Part 2.
    # Backfill them before adding the NOT NULL and UNIQUE constraints.
    op.execute(
        "UPDATE checkout_sessions SET idempotency_key = 'legacy-' || id WHERE idempotency_key IS NULL"
    )

    with op.batch_alter_table("checkout_sessions") as batch:
        batch.create_foreign_key(
            "fk_checkout_sessions_order", "orders", ["order_id"], ["id"]
        )
        batch.create_unique_constraint(
            "uq_checkout_sessions_idempotency", ["idempotency_key"]
        )
        batch.alter_column(
            "idempotency_key", nullable=False, existing_type=sa.String(80)
        )
        batch.create_unique_constraint("uq_checkout_sessions_order", ["order_id"])
        batch.alter_column(
            "subtotal", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(10, 2)
        )
        batch.alter_column(
            "discount", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(10, 2)
        )
        batch.alter_column(
            "total", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(10, 2)
        )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_checkout_sessions_active_account ON checkout_sessions (account_id) WHERE payment_status IN ('PENDING', 'PAYMENT_PENDING', 'PAID') AND order_id IS NULL"
    )

    with op.batch_alter_table("payments") as batch:
        batch.add_column(sa.Column("checkout_session_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("gateway_order_id", sa.String(255), nullable=True))
        batch.add_column(sa.Column("failure_message", sa.String(500), nullable=True))
        batch.create_foreign_key(
            "fk_payments_checkout_session",
            "checkout_sessions",
            ["checkout_session_id"],
            ["id"],
        )
        batch.create_unique_constraint(
            "uq_payments_checkout_session", ["checkout_session_id"]
        )
        batch.create_unique_constraint(
            "uq_payments_gateway_order", ["gateway_order_id"]
        )
        batch.alter_column(
            "amount", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(10, 2)
        )

    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("coupon_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "taxable_base", sa.Numeric(12, 2), nullable=False, server_default="0"
            )
        )
        batch.add_column(
            sa.Column(
                "marketing_fee", sa.Numeric(12, 2), nullable=False, server_default="0"
            )
        )
        batch.add_column(
            sa.Column("tax", sa.Numeric(12, 2), nullable=False, server_default="0")
        )
        for name in (
            "customer_name",
            "delivery_full_name",
            "delivery_phone",
            "delivery_address_line_1",
            "delivery_city",
            "delivery_state",
            "delivery_postal_code",
        ):
            batch.add_column(
                sa.Column(name, sa.String(255), nullable=False, server_default="")
            )
        batch.add_column(
            sa.Column(
                "customer_email", sa.String(255), nullable=False, server_default=""
            )
        )
        batch.add_column(
            sa.Column("delivery_address_line_2", sa.String(255), nullable=True)
        )
        batch.add_column(sa.Column("delivery_landmark", sa.String(255), nullable=True))
        batch.add_column(
            sa.Column(
                "delivery_country",
                sa.String(100),
                nullable=False,
                server_default="India",
            )
        )
        batch.add_column(sa.Column("cancellation_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("cancelled_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_orders_coupon", "coupons", ["coupon_id"], ["id"])
        batch.alter_column(
            "subtotal", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(10, 2)
        )
        batch.alter_column(
            "discount", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(10, 2)
        )
        batch.alter_column(
            "total", type_=sa.Numeric(12, 2), existing_type=sa.Numeric(10, 2)
        )

    op.create_table(
        "invoices",
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(80), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
        sa.UniqueConstraint("invoice_number"),
    )

    op.create_table(
        "order_events",
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"])
    op.create_index("ix_order_events_occurred_at", "order_events", ["occurred_at"])

    op.create_table(
        "return_requests",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="REQUESTED"),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["order_item_id"], ["order_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_return_requests_account_id", "return_requests", ["account_id"])
    op.create_index("ix_return_requests_order_id", "return_requests", ["order_id"])
    op.create_index(
        "ix_return_requests_order_item_id", "return_requests", ["order_item_id"]
    )
    op.create_index("ix_return_requests_status", "return_requests", ["status"])

    op.create_table(
        "stock_alert_subscriptions",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["product_variants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stock_alert_subscriptions_account_id",
        "stock_alert_subscriptions",
        ["account_id"],
    )
    op.create_index(
        "ix_stock_alert_subscriptions_product_id",
        "stock_alert_subscriptions",
        ["product_id"],
    )
    op.create_index(
        "ix_stock_alert_subscriptions_variant_id",
        "stock_alert_subscriptions",
        ["variant_id"],
    )
    op.create_index(
        "uq_stock_alert_product_variant",
        "stock_alert_subscriptions",
        ["account_id", "product_id", "variant_id"],
        unique=True,
        postgresql_where=sa.text("variant_id IS NOT NULL"),
    )
    op.create_index(
        "uq_stock_alert_product",
        "stock_alert_subscriptions",
        ["account_id", "product_id"],
        unique=True,
        postgresql_where=sa.text("variant_id IS NULL"),
    )

    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("dedupe_key", sa.String(255), nullable=True))
        batch.create_unique_constraint("uq_notifications_dedupe_key", ["dedupe_key"])


def downgrade():
    with op.batch_alter_table("order_items") as batch:
        batch.drop_column("variant_value_snapshot")
        batch.drop_column("variant_name_snapshot")
        batch.drop_column("product_name_snapshot")

    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("uq_notifications_dedupe_key", type_="unique")
        batch.drop_column("dedupe_key")

    op.drop_index("uq_stock_alert_product", table_name="stock_alert_subscriptions")
    op.drop_index(
        "uq_stock_alert_product_variant", table_name="stock_alert_subscriptions"
    )

    for table in (
        "stock_alert_subscriptions",
        "return_requests",
        "order_events",
        "invoices",
    ):
        op.drop_table(table)

    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("fk_orders_coupon", type_="foreignkey")
        for name in (
            "coupon_id",
            "taxable_base",
            "marketing_fee",
            "tax",
            "customer_name",
            "customer_email",
            "delivery_full_name",
            "delivery_phone",
            "delivery_address_line_1",
            "delivery_address_line_2",
            "delivery_landmark",
            "delivery_city",
            "delivery_state",
            "delivery_postal_code",
            "delivery_country",
            "cancellation_reason",
            "cancelled_at",
        ):
            batch.drop_column(name)

    with op.batch_alter_table("payments") as batch:
        batch.drop_constraint("fk_payments_checkout_session", type_="foreignkey")
        batch.drop_constraint("uq_payments_checkout_session", type_="unique")
        batch.drop_constraint("uq_payments_gateway_order", type_="unique")
        batch.drop_column("checkout_session_id")
        batch.drop_column("gateway_order_id")
        batch.drop_column("failure_message")

    op.execute("DROP INDEX IF EXISTS uq_checkout_sessions_active_account")
    with op.batch_alter_table("checkout_sessions") as batch:
        batch.drop_constraint("fk_checkout_sessions_order", type_="foreignkey")
        batch.drop_constraint("uq_checkout_sessions_idempotency", type_="unique")
        batch.drop_constraint("uq_checkout_sessions_order", type_="unique")
        for name in (
            "order_id",
            "taxable_base",
            "marketing_fee",
            "tax",
            "idempotency_key",
            "payment_error",
        ):
            batch.drop_column(name)
