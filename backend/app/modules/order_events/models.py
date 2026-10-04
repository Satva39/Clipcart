from datetime import datetime

from app.extensions import db
from app.shared.models.base_model import BaseModel


class OrderEvent(BaseModel):
    __tablename__ = "order_events"

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=True)
    occurred_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    order = db.relationship(
        "Order",
        backref=db.backref(
            "events",
            lazy="dynamic",
            cascade="all, delete-orphan",
            order_by="OrderEvent.occurred_at.asc()",
        ),
    )
