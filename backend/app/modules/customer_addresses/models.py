from app.extensions import db
from app.shared.models.base_model import BaseModel


class CustomerAddress(BaseModel):

    __tablename__ = "customer_addresses"

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
    )

    full_name = db.Column(
        db.String(150),
        nullable=False,
    )

    phone = db.Column(
        db.String(20),
        nullable=False,
    )

    address_line_1 = db.Column(
        db.String(255),
        nullable=False,
    )

    address_line_2 = db.Column( 
        db.String(255),
        nullable=True,
    )

    landmark = db.Column(
        db.String(255),
        nullable=True,
    )

    city = db.Column(
        db.String(100),
        nullable=False,
    )

    state = db.Column(
        db.String(100),
        nullable=False,
    )

    postal_code = db.Column(
        db.String(20),
        nullable=False,
    )

    country = db.Column(
        db.String(100),
        default="India",
        nullable=False,
    )

    is_default = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    account = db.relationship(
        "Account",
        back_populates="customer_addresses",
    )