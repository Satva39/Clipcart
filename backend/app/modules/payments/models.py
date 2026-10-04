from app.extensions import db
from app.shared.models.base_model import BaseModel


class Payment(BaseModel):
    __tablename__ = "payments"
    __table_args__ = (
        db.CheckConstraint("amount >= 0", name="ck_payments_amount_nonnegative"),
    )

    account_id = db.Column(
        db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True
    )
    checkout_session_id = db.Column(
        db.Integer,
        db.ForeignKey("checkout_sessions.id"),
        nullable=True,
        unique=True,
    )
    gateway_order_id = db.Column(db.String(255), unique=True, nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)
    gateway = db.Column(db.String(50), default="RAZORPAY", nullable=False)
    transaction_id = db.Column(db.String(255), unique=True, nullable=True)
    status = db.Column(db.String(30), default="PENDING", nullable=False, index=True)
    failure_message = db.Column(db.String(500), nullable=True)

    account = db.relationship("Account", backref="payments")
    checkout_session = db.relationship(
        "CheckoutSession", backref=db.backref("payment", uselist=False)
    )
