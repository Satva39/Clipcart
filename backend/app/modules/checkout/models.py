from app.extensions import db
from app.shared.models.base_model import BaseModel


class CheckoutSession(BaseModel):
    __tablename__ = "checkout_sessions"

    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True
    )
    address_id = db.Column(
        db.Integer, db.ForeignKey("customer_addresses.id"), nullable=True
    )
    coupon_id = db.Column(db.Integer, db.ForeignKey("coupons.id"), nullable=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=True, unique=True
    )

    subtotal = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    discount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    taxable_base = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    marketing_fee = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    tax = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    total = db.Column(db.Numeric(12, 2), default=0, nullable=False)

    payment_status = db.Column(
        db.String(30), default="PENDING", nullable=False, index=True
    )
    idempotency_key = db.Column(db.String(80), nullable=False, unique=True)

    razorpay_order_id = db.Column(db.String(255), nullable=True, unique=True)
    razorpay_payment_id = db.Column(db.String(255), nullable=True, unique=True)
    razorpay_signature = db.Column(db.String(500), nullable=True)
    payment_error = db.Column(db.String(500), nullable=True)

    account = db.relationship("Account", backref="checkout_sessions")
    address = db.relationship("CustomerAddress", backref="checkout_sessions")
    coupon = db.relationship("Coupon", backref="checkout_sessions")
    order = db.relationship("Order", backref="checkout_session")
