"""Clipcart Part 5 admin controls, settings, banners, audit and auth revocation.

Revision ID: a5b6c7d8e9f0
Revises: 9d4c6a3e2f11
"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "a5b6c7d8e9f0"
down_revision = "9d4c6a3e2f11"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("token_type", sa.String(length=30), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index("ix_revoked_tokens_jti", "revoked_tokens", ["jti"])
    op.create_index("ix_revoked_tokens_account_id", "revoked_tokens", ["account_id"])
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])

    op.create_table(
        "admin_audit_logs",
        sa.Column("admin_account_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["admin_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_audit_logs_admin_account_id", "admin_audit_logs", ["admin_account_id"]
    )
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index(
        "ix_admin_audit_logs_resource_type", "admin_audit_logs", ["resource_type"]
    )
    op.create_index(
        "ix_admin_audit_logs_resource_id", "admin_audit_logs", ["resource_id"]
    )
    op.create_index(
        "ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"]
    )

    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column(
            "is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_platform_settings_key", "platform_settings", ["key"])
    op.create_index(
        "ix_platform_settings_is_public", "platform_settings", ["is_public"]
    )

    op.create_table(
        "admin_banners",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
        sa.Column("cta_label", sa.String(length=100), nullable=True),
        sa.Column("destination", sa.String(length=1000), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_banners_is_active", "admin_banners", ["is_active"])
    op.create_index("ix_admin_banners_starts_at", "admin_banners", ["starts_at"])
    op.create_index("ix_admin_banners_ends_at", "admin_banners", ["ends_at"])
    op.create_index("ix_admin_banners_sort_order", "admin_banners", ["sort_order"])

    op.create_index(
        "ix_accounts_role_status",
        "accounts",
        ["role", "status"],
        unique=False,
    )
    op.create_index(
        "ix_orders_created_at_status",
        "orders",
        ["created_at", "status"],
        unique=False,
    )
    op.create_index(
        "ix_payments_created_at_status",
        "payments",
        ["created_at", "status"],
        unique=False,
    )
    op.create_index(
        "ix_supplier_payouts_created_at_status",
        "supplier_payouts",
        ["created_at", "status"],
        unique=False,
    )
    op.create_index(
        "ix_delivery_assignments_statuses",
        "delivery_assignments",
        ["pickup_status", "delivery_status"],
        unique=False,
    )
    op.create_index(
        "ix_products_seller_status_featured",
        "products",
        ["seller_id", "status", "is_featured"],
        unique=False,
    )

    op.create_check_constraint(
        "ck_products_stock_nonnegative",
        "products",
        "stock >= 0",
    )
    op.create_check_constraint(
        "ck_product_variants_stock_nonnegative",
        "product_variants",
        "stock >= 0",
    )
    op.create_check_constraint(
        "ck_payments_amount_nonnegative",
        "payments",
        "amount >= 0",
    )
    op.create_check_constraint(
        "ck_supplier_payouts_amount_positive",
        "supplier_payouts",
        "amount > 0",
    )

    settings = sa.table(
        "platform_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.JSON),
        sa.column("is_public", sa.Boolean),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    seed_timestamp = datetime.utcnow()
    op.bulk_insert(
        settings,
        [
            {
                "key": "marketing_fee",
                "value": 2.0,
                "is_public": False,
                "description": "Fixed Clipcart marketing fee added to customer checkout.",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
            {
                "key": "tax_threshold",
                "value": 2000.0,
                "is_public": False,
                "description": "Tax applies above this discounted merchandise subtotal.",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
            {
                "key": "tax_rate",
                "value": 0.18,
                "is_public": False,
                "description": "Tax rate used by checkout calculations.",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
            {
                "key": "tax_cap",
                "value": 500.0,
                "is_public": False,
                "description": "Maximum tax charged on one checkout.",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
            {
                "key": "supplier_registration_fee",
                "value": 50.0,
                "is_public": False,
                "description": "One-time supplier onboarding fee.",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
            {
                "key": "customer_announcement",
                "value": "",
                "is_public": True,
                "description": "Optional customer-facing announcement shown on the storefront.",
                "created_at": seed_timestamp,
                "updated_at": seed_timestamp,
            },
        ],
    )


def downgrade():
    op.drop_constraint(
        "ck_supplier_payouts_amount_positive", "supplier_payouts", type_="check"
    )
    op.drop_constraint("ck_payments_amount_nonnegative", "payments", type_="check")
    op.drop_constraint(
        "ck_product_variants_stock_nonnegative", "product_variants", type_="check"
    )
    op.drop_constraint("ck_products_stock_nonnegative", "products", type_="check")

    for name, table in [
        ("ix_products_seller_status_featured", "products"),
        ("ix_delivery_assignments_statuses", "delivery_assignments"),
        ("ix_supplier_payouts_created_at_status", "supplier_payouts"),
        ("ix_payments_created_at_status", "payments"),
        ("ix_orders_created_at_status", "orders"),
        ("ix_accounts_role_status", "accounts"),
    ]:
        op.drop_index(name, table_name=table)

    for name in [
        "ix_admin_banners_sort_order",
        "ix_admin_banners_ends_at",
        "ix_admin_banners_starts_at",
        "ix_admin_banners_is_active",
    ]:
        op.drop_index(name, table_name="admin_banners")
    op.drop_table("admin_banners")

    op.drop_index("ix_platform_settings_is_public", table_name="platform_settings")
    op.drop_index("ix_platform_settings_key", table_name="platform_settings")
    op.drop_table("platform_settings")

    for name in [
        "ix_admin_audit_logs_created_at",
        "ix_admin_audit_logs_resource_id",
        "ix_admin_audit_logs_resource_type",
        "ix_admin_audit_logs_action",
        "ix_admin_audit_logs_admin_account_id",
    ]:
        op.drop_index(name, table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")

    for name in [
        "ix_revoked_tokens_expires_at",
        "ix_revoked_tokens_account_id",
        "ix_revoked_tokens_jti",
    ]:
        op.drop_index(name, table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
