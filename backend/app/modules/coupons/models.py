from sqlalchemy import Numeric

from app.extensions import db
from app.shared.models.base_model import BaseModel

from .enums import DiscountType


class Coupon(BaseModel):

    __tablename__ = "coupons"

    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=True,
    )

    code = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
    )

    discount_type = db.Column(
        db.Enum(DiscountType),
        nullable=False,
    )

    discount_value = db.Column(
        Numeric(10, 2),
        nullable=False,
    )

    minimum_order = db.Column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    maximum_discount = db.Column(
        Numeric(10, 2),
        nullable=True,
    )

    usage_limit = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    used_count = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    seller = db.relationship(
        "Account",
        backref="coupons",
    )