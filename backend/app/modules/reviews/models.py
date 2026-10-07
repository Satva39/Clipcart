from app.extensions import db
from app.shared.models.base_model import BaseModel

from .media_models import ReviewMedia


class Review(BaseModel):

    __tablename__ = "reviews"

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

    order_item_id = db.Column(
        db.Integer,
        db.ForeignKey("order_items.id"),
        nullable=False,
        unique=True,
    )

    rating = db.Column(
        db.Integer,
        nullable=False,
    )

    title = db.Column(
        db.String(255),
        nullable=True,
    )

    review = db.Column(
        db.Text,
        nullable=True,
    )

    is_verified_purchase = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )

    is_approved = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    account = db.relationship(
        "Account",
        backref="reviews",
    )

    product = db.relationship(
        "Product",
        backref="reviews",
    )

    order_item = db.relationship(
        "OrderItem",
        backref="review",
    )

    media = db.relationship(
        "ReviewMedia",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewMedia.sort_order",
    )
