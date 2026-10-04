from app.extensions import db
from app.shared.models.base_model import BaseModel


class StockAlertSubscription(BaseModel):
    __tablename__ = "stock_alert_subscriptions"

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id = db.Column(
        db.Integer,
        db.ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        db.Index(
            "uq_stock_alert_product_variant",
            "account_id",
            "product_id",
            "variant_id",
            unique=True,
            postgresql_where=variant_id.isnot(None),
        ),
        db.Index(
            "uq_stock_alert_product",
            "account_id",
            "product_id",
            unique=True,
            postgresql_where=variant_id.is_(None),
        ),
    )

    account = db.relationship("Account", backref="stock_alert_subscriptions")
    product = db.relationship("Product", backref="stock_alert_subscriptions")
    variant = db.relationship("ProductVariant", backref="stock_alert_subscriptions")
