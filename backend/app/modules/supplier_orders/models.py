from app.extensions import db
from app.shared.models.base_model import BaseModel

from .enums import PickupStatus, DeliveryStatus


class DeliveryAssignment(BaseModel):

    __tablename__ = "delivery_assignments"

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False,
        unique=True,
    )

    assigned_by_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=True,
    )

    agent_name = db.Column(
        db.String(150),
        nullable=True,
    )

    agent_phone = db.Column(
        db.String(30),
        nullable=True,
    )

    assigned_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    pickup_status = db.Column(
        db.Enum(PickupStatus),
        default=PickupStatus.PENDING,
        nullable=False,
    )

    pickup_time = db.Column(
        db.DateTime,
        nullable=True,
    )

    delivery_status = db.Column(
        db.Enum(DeliveryStatus),
        default=DeliveryStatus.NOT_STARTED,
        nullable=False,
    )

    delivery_time = db.Column(
        db.DateTime,
        nullable=True,
    )

    out_for_delivery_time = db.Column(
        db.DateTime,
        nullable=True,
    )

    delivery_attempts = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    last_attempt_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    last_attempt_reason = db.Column(
        db.Text,
        nullable=True,
    )

    failed_reason = db.Column(
        db.Text,
        nullable=True,
    )

    next_action = db.Column(
        db.String(255),
        nullable=True,
    )

    customer_delivery_notes = db.Column(
        db.Text,
        nullable=True,
    )

    proof_of_delivery_reference = db.Column(
        db.String(500),
        nullable=True,
    )

    proof_of_delivery_image_url = db.Column(
        db.String(500),
        nullable=True,
    )

    proof_of_delivery_image_public_id = db.Column(
        db.String(255),
        nullable=True,
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    order = db.relationship(
        "Order",
        backref=db.backref(
            "delivery_assignment",
            uselist=False,
        ),
    )

    assigned_by = db.relationship(
        "Account",
        foreign_keys=[assigned_by_id],
    )
