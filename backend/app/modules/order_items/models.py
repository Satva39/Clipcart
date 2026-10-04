from app.extensions import db
from app.shared.models.base_model import BaseModel


class OrderItem(BaseModel):

    __tablename__ = "order_items"

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False,
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
    )

    variant_id = db.Column(
        db.Integer,
        db.ForeignKey("product_variants.id"),
        nullable=True,
    )

    product_name_snapshot = db.Column(
        db.String(255),
        nullable=False,
        default="",
    )

    variant_name_snapshot = db.Column(
        db.String(100),
        nullable=True,
    )

    variant_value_snapshot = db.Column(
        db.String(255),
        nullable=True,
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
    )

    unit_price = db.Column(
        db.Numeric(10, 2),
        nullable=False,
    )

    subtotal = db.Column(
        db.Numeric(10, 2),
        nullable=False,
    )

    order = db.relationship(
        "Order",
        back_populates="items",
    )

    product = db.relationship(
        "Product",
        backref="order_items",
    )

    variant = db.relationship(
        "ProductVariant",
        backref="order_items",
    )
