from flask import Flask
from datetime import datetime
from flask_cors import CORS

from .config import Config
from .core.errors import register_error_handlers
from .extensions import db, jwt, ma, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
    )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)

    # Import models once so SQLAlchemy metadata and Flask-Migrate can discover them.
    from app.modules.accounts.models import Account  # noqa: F401
    from app.modules.brands.models import Brand  # noqa: F401
    from app.modules.cart.models import CartItem  # noqa: F401
    from app.modules.categories.models import Category  # noqa: F401
    from app.modules.checkout.models import CheckoutSession  # noqa: F401
    from app.modules.coupons.models import Coupon  # noqa: F401
    from app.modules.customer_addresses.models import CustomerAddress  # noqa: F401
    from app.modules.inventory.models import InventoryLog  # noqa: F401
    from app.modules.order_events.models import OrderEvent  # noqa: F401
    from app.modules.invoices.models import Invoice  # noqa: F401
    from app.modules.returns.models import (
        # ReturnDeliveryAssignment,
        ReturnRequest,
    )  # noqa: F401
    from app.modules.stock_alerts.models import StockAlertSubscription  # noqa: F401
    from app.modules.notifications.models import Notification  # noqa: F401
    from app.modules.order_items.models import OrderItem  # noqa: F401
    from app.modules.orders.models import Order  # noqa: F401
    from app.modules.payments.models import Payment  # noqa: F401
    from app.modules.payouts.models import (
        SupplierPayout,
        SupplierPayoutAccount,
    )  # noqa: F401
    from app.modules.product_images.models import ProductImage  # noqa: F401
    from app.modules.product_variants.models import ProductVariant  # noqa: F401
    from app.modules.products.models import Product  # noqa: F401
    from app.modules.reviews.models import Review  # noqa: F401
    from app.modules.seller_verification.models import SellerVerification  # noqa: F401
    from app.modules.supplier_orders.models import DeliveryAssignment  # noqa: F401
    from app.modules.shiprocket.models import Shipment  # noqa: F401
    from app.modules.wishlist.models import WishlistItem  # noqa: F401
    from app.modules.admin.models import (
        AdminAuditLog,
        AdminBanner,
        PlatformSetting,
    )  # noqa: F401
    from app.modules.auth.models import RevokedToken  # noqa: F401

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(_jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        if not jti:
            return False
        revoked = RevokedToken.query.filter_by(jti=jti).first()
        if revoked and revoked.expires_at <= datetime.utcnow():
            try:
                db.session.delete(revoked)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return False
        return revoked is not None

    @jwt.revoked_token_loader
    def revoked_token_response(_jwt_header, _jwt_payload):
        return (
            {"success": False, "message": "Session has been revoked.", "data": None},
            401,
        )

    from .routes import register_routes

    register_routes(app)
    register_error_handlers(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), camera=(), microphone=()",
        )
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    return app
