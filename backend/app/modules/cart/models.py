from app.extensions import db
from app.shared.models.base_model import BaseModel


class CartItem(BaseModel):

    __tablename__ = "cart_items"

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
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

    quantity = db.Column(
        db.Integer,
        default=1,
        nullable=False,
    )

    account = db.relationship(
        "Account",
        backref="cart_items",
    )

    product = db.relationship(
        "Product",
        backref="cart_items",
    )

    variant = db.relationship(
        "ProductVariant",
        backref="cart_items",
    )