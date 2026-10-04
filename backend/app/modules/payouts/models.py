from app.extensions import db
from app.shared.models.base_model import BaseModel


class SupplierPayoutAccount(BaseModel):

    __tablename__ = "supplier_payout_accounts"

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
        unique=True,
    )

    holder_name = db.Column(
        db.String(150),
        nullable=False,
    )

    bank_name = db.Column(
        db.String(150),
        nullable=True,
    )

    account_number = db.Column(
        db.String(100),
        nullable=True,
    )

    ifsc = db.Column(
        db.String(20),
        nullable=True,
    )

    upi_id = db.Column(
        db.String(150),
        nullable=True,
    )

    is_verified = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    account = db.relationship(
        "Account",
        backref=db.backref(
            "supplier_payout_account",
            uselist=False,
        ),
    )


class SupplierPayout(BaseModel):

    __tablename__ = "supplier_payouts"
    __table_args__ = (
        db.CheckConstraint(
            "amount > 0",
            name="ck_supplier_payouts_amount_positive",
        ),
    )

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
    )

    payout_account_id = db.Column(
        db.Integer,
        db.ForeignKey("supplier_payout_accounts.id"),
        nullable=False,
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
    )

    status = db.Column(
        db.String(30),
        default="PENDING",
        nullable=False,
    )

    reference_id = db.Column(
        db.String(255),
        unique=True,
        nullable=True,
    )

    processed_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    account = db.relationship(
        "Account",
        backref="supplier_payouts",
    )

    payout_account = db.relationship(
        "SupplierPayoutAccount",
        backref="payouts",
    )
