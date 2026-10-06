from app.extensions import db
from app.shared.models.base_model import BaseModel


class Shipment(BaseModel):
    __tablename__ = "shipments"
    __table_args__ = (
        db.UniqueConstraint(
            "order_id", "supplier_id", name="uq_shipments_order_supplier"
        ),
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )

    # Our deterministic source order reference sent to Shiprocket.
    shiprocket_reference_id = db.Column(
        db.String(50), nullable=False, unique=True, index=True
    )
    shiprocket_order_id = db.Column(db.Integer, nullable=True, index=True)
    shiprocket_shipment_id = db.Column(db.Integer, nullable=True, index=True)

    awb_code = db.Column(db.String(128), nullable=True, index=True)
    courier_company_id = db.Column(db.Integer, nullable=True)
    courier_name = db.Column(db.String(255), nullable=True)

    pickup_location_id = db.Column(db.String(64), nullable=True)
    pickup_location = db.Column(db.String(100), nullable=True)

    status = db.Column(db.String(80), nullable=False, default="PENDING", index=True)
    status_id = db.Column(db.Integer, nullable=True)
    failure_code = db.Column(db.String(80), nullable=True)
    failure_message = db.Column(db.Text, nullable=True)

    last_synced_at = db.Column(db.DateTime, nullable=True)
    last_webhook_at = db.Column(db.DateTime, nullable=True)
    last_webhook_hash = db.Column(db.String(64), nullable=True)
    pickup_scheduled_at = db.Column(db.DateTime, nullable=True)
    awb_assigned_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    label_url = db.Column(db.Text, nullable=True)
    tracking_url = db.Column(db.Text, nullable=True)
    estimated_delivery_at = db.Column(db.DateTime, nullable=True)
    tracking_data = db.Column(db.JSON, nullable=True)
    tracking_events = db.Column(db.JSON, nullable=True)
    last_tracking_event_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship(
        "Order",
        backref=db.backref("shipments", lazy="selectin", cascade="all, delete-orphan"),
    )
    supplier = db.relationship("Account", foreign_keys=[supplier_id])
