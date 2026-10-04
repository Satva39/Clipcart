from app.extensions import db
from app.shared.models.base_model import BaseModel


class SellerVerification(BaseModel):

    __tablename__ = "seller_verifications"

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
        unique=True,
    )

    registration_fee_paid = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    payment_id = db.Column(
        db.String(255),
        nullable=True,
    )

    business_name = db.Column(
        db.String(255),
        nullable=True,
    )

    gst_number = db.Column(
        db.String(50),
        nullable=True,
    )

    status = db.Column(
        db.String(30),
        default="PENDING",
        nullable=False,
    )

    return_address_line_1 = db.Column(db.String(255), nullable=True)
    return_address_line_2 = db.Column(db.String(255), nullable=True)
    return_landmark = db.Column(db.String(255), nullable=True)
    return_city = db.Column(db.String(100), nullable=True)
    return_state = db.Column(db.String(100), nullable=True)
    return_postal_code = db.Column(db.String(20), nullable=True)
    return_country = db.Column(db.String(100), nullable=False, default="India")

    account = db.relationship(
        "Account",
        backref=db.backref("seller_verification", uselist=False),
    )
