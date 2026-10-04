from app.extensions import db
from app.shared.models.base_model import BaseModel


class WishlistItem(BaseModel):

    __tablename__ = "wishlist_items"

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

    account = db.relationship(
        "Account",
        backref="wishlist_items",
    )

    product = db.relationship(
        "Product",
        backref="wishlisted_by",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "account_id",
            "product_id",
            name="uq_wishlist_account_product",
        ),
    )