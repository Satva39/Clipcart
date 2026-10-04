import uuid

from app.extensions import db
from app.shared.models.base_model import BaseModel

from .enums import UserRole, UserStatus


class Account(BaseModel):

    __tablename__ = "accounts"

    uuid = db.Column(
        db.String(36),
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
    )

    full_name = db.Column(
        db.String(150),
        nullable=False,
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    phone = db.Column(
        db.String(20),
        unique=True,
        nullable=True,
    )

    role = db.Column(
        db.Enum(UserRole),
        nullable=False,
        default=UserRole.CUSTOMER,
    )

    status = db.Column(
        db.Enum(UserStatus),
        nullable=False,
        default=UserStatus.PENDING,
    )

    email_verified = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    phone_verified = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    profile_image = db.Column(
        db.String(500),
        nullable=True,
    )

    last_login = db.Column(
        db.DateTime,
        nullable=True,
    )

    products = db.relationship(
        "Product",
        back_populates="seller",
        lazy=True,
    )

    customer_addresses  = db.relationship(
        "CustomerAddress",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy=True,
    )