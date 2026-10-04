from app.extensions import db
from app.shared.models.base_model import BaseModel

from .enums import OrderStatus


class Order(BaseModel):
    __tablename__ = "orders"

    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True
    )
    address_id = db.Column(
        db.Integer, db.ForeignKey("customer_addresses.id"), nullable=True
    )
    payment_id = db.Column(
        db.Integer, db.ForeignKey("payments.id"), nullable=True, index=True
    )
    coupon_id = db.Column(db.Integer, db.ForeignKey("coupons.id"), nullable=True)

    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    taxable_base = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    marketing_fee = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    tax = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    customer_name = db.Column(db.String(150), nullable=False, default="")
    customer_email = db.Column(db.String(255), nullable=False, default="")
    delivery_full_name = db.Column(db.String(150), nullable=False, default="")
    delivery_phone = db.Column(db.String(20), nullable=False, default="")
    delivery_address_line_1 = db.Column(db.String(255), nullable=False, default="")
    delivery_address_line_2 = db.Column(db.String(255), nullable=True)
    delivery_landmark = db.Column(db.String(255), nullable=True)
    delivery_city = db.Column(db.String(100), nullable=False, default="")
    delivery_state = db.Column(db.String(100), nullable=False, default="")
    delivery_postal_code = db.Column(db.String(20), nullable=False, default="")
    delivery_country = db.Column(db.String(100), nullable=False, default="India")

    status = db.Column(
        db.Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True
    )
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    account = db.relationship("Account", backref="orders")
    address = db.relationship("CustomerAddress", backref="orders")
    payment = db.relationship("Payment", backref="orders", foreign_keys=[payment_id])
    coupon = db.relationship("Coupon", backref="orders")
    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
