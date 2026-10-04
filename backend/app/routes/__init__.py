from flask import jsonify
from sqlalchemy import text

from app.modules.accounts.routes import accounts_bp
from app.modules.admin.routes import admin_bp
from app.modules.brands import brands_bp
from app.modules.cart.routes import cart_bp
from app.modules.categories.routes import categories_bp
from app.modules.checkout.routes import checkout_bp
from app.modules.coupons.routes import coupons_bp
from app.modules.customer_addresses.routes import customer_addresses_bp
from app.modules.inventory.routes import inventory_bp
from app.modules.notifications import notifications_bp
from app.modules.orders.routes import orders_bp
from app.modules.returns.routes import returns_bp
from app.modules.stock_alerts.routes import stock_alerts_bp
from app.modules.payments.routes import payments_bp
from app.modules.payouts.routes import payouts_bp
from app.modules.product_images.routes import product_images_bp
from app.modules.product_variants.routes import product_variants_bp
from app.modules.products.routes import products_bp
from app.modules.reviews.routes import reviews_bp
from app.modules.seller_verification.routes import seller_verification_bp
from app.modules.store.routes import store_bp
from app.modules.supplier_dashboard.routes import supplier_dashboard_bp
from app.modules.supplier_orders.routes import supplier_orders_bp
from app.modules.supplier_portal import supplier_portal_bp
from app.modules.supplier_registration.routes import supplier_registration_bp
from app.modules.trending import trending_bp
from app.modules.uploads.routes import upload_bp
from app.modules.wishlist.routes import wishlist_bp


def register_routes(app):
    @app.get("/api")
    def api_root():
        return jsonify(
            {
                "success": True,
                "message": "Welcome to Clipcart API",
                "data": {
                    "name": "Clipcart",
                    "version": "1.0",
                    "status": "ok",
                },
            }
        )

    @app.get("/api/health")
    def api_health():
        from app.extensions import db

        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(
                {
                    "success": True,
                    "message": "Clipcart API is healthy.",
                    "data": {"status": "ok", "database": "ok"},
                }
            )
        except Exception:
            db.session.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Clipcart API database health check failed.",
                        "data": {"status": "degraded"},
                    }
                ),
                503,
            )

    blueprints = (
        accounts_bp,
        products_bp,
        categories_bp,
        product_images_bp,
        product_variants_bp,
        upload_bp,
        inventory_bp,
        supplier_dashboard_bp,
        seller_verification_bp,
        payments_bp,
        store_bp,
        wishlist_bp,
        cart_bp,
        checkout_bp,
        orders_bp,
        returns_bp,
        stock_alerts_bp,
        reviews_bp,
        coupons_bp,
        customer_addresses_bp,
        notifications_bp,
        trending_bp,
        brands_bp,
        supplier_registration_bp,
        payouts_bp,
        supplier_orders_bp,
        supplier_portal_bp,
        admin_bp,
    )

    for blueprint in blueprints:
        app.register_blueprint(blueprint)
