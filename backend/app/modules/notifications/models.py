from app.extensions import db
from app.shared.models.base_model import BaseModel

from .enums import NotificationType


class Notification(BaseModel):

    __tablename__ = "notifications"

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
    )

    title = db.Column(
        db.String(255),
        nullable=False,
    )

    message = db.Column(
        db.Text,
        nullable=False,
    )

    notification_type = db.Column(
        db.String(50),
        nullable=False,
    )

    is_read = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    dedupe_key = db.Column(
        db.String(255),
        unique=True,
        nullable=True,
    )

    account = db.relationship(
        "Account",
        backref="notifications",
    )
