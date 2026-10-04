"""Add targeted indexes for high-frequency Clipcart read paths.

Revision ID: 7c3e9b1a2d44
Revises: 121241a0d4d0
"""

from alembic import op

revision = "7c3e9b1a2d44"
down_revision = "121241a0d4d0"
branch_labels = None
depends_on = None


def upgrade():
    indexes = [
        ("ix_products_status_created_at", "products", ["status", "created_at"]),
        ("ix_products_category_status", "products", ["category_id", "status"]),
        ("ix_product_variants_product_id", "product_variants", ["product_id"]),
        (
            "ix_product_images_product_sort",
            "product_images",
            ["product_id", "sort_order"],
        ),
        ("ix_product_images_variant_id", "product_images", ["variant_id"]),
        ("ix_reviews_product_approved", "reviews", ["product_id", "is_approved"]),
        ("ix_reviews_account_id", "reviews", ["account_id"]),
        ("ix_order_items_order_id", "order_items", ["order_id"]),
        ("ix_order_items_product_id", "order_items", ["product_id"]),
        ("ix_order_items_variant_id", "order_items", ["variant_id"]),
        (
            "ix_cart_items_account_product_variant",
            "cart_items",
            ["account_id", "product_id", "variant_id"],
        ),
        ("ix_customer_addresses_account_id", "customer_addresses", ["account_id"]),
        (
            "ix_notifications_account_read_created",
            "notifications",
            ["account_id", "is_read", "created_at"],
        ),
        (
            "ix_inventory_logs_variant_created",
            "inventory_logs",
            ["variant_id", "created_at"],
        ),
        (
            "ix_inventory_logs_product_created",
            "inventory_logs",
            ["product_id", "created_at"],
        ),
        (
            "ix_supplier_payouts_account_status",
            "supplier_payouts",
            ["account_id", "status"],
        ),
    ]

    for name, table, columns in indexes:
        op.create_index(name, table, columns, unique=False)


def downgrade():
    indexes = [
        ("ix_supplier_payouts_account_status", "supplier_payouts"),
        ("ix_inventory_logs_product_created", "inventory_logs"),
        ("ix_inventory_logs_variant_created", "inventory_logs"),
        ("ix_notifications_account_read_created", "notifications"),
        ("ix_customer_addresses_account_id", "customer_addresses"),
        ("ix_cart_items_account_product_variant", "cart_items"),
        ("ix_order_items_variant_id", "order_items"),
        ("ix_order_items_product_id", "order_items"),
        ("ix_order_items_order_id", "order_items"),
        ("ix_reviews_account_id", "reviews"),
        ("ix_reviews_product_approved", "reviews"),
        ("ix_product_images_variant_id", "product_images"),
        ("ix_product_images_product_sort", "product_images"),
        ("ix_product_variants_product_id", "product_variants"),
        ("ix_products_category_status", "products"),
        ("ix_products_status_created_at", "products"),
    ]
    for name, table in indexes:
        op.drop_index(name, table_name=table)
