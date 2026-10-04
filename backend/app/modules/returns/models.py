from app.extensions import db
from app.shared.models.base_model import BaseModel


class ReturnRequest(BaseModel):
    __tablename__ = "return_requests"

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id = db.Column(
        db.Integer,
        db.ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="REQUESTED", index=True)
    resolution_note = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    logistics_agent_name = db.Column(db.String(150), nullable=True)
    logistics_agent_phone = db.Column(db.String(30), nullable=True)
    logistics_assigned_at = db.Column(db.DateTime, nullable=True)
    customer_picked_up_at = db.Column(db.DateTime, nullable=True)
    supplier_received_at = db.Column(db.DateTime, nullable=True)
    logistics_notes = db.Column(db.Text, nullable=True)

    completion_image_url = db.Column(db.String(500), nullable=True)
    completion_image_public_id = db.Column(db.String(255), nullable=True)

    account = db.relationship("Account", backref="return_requests")
    order = db.relationship("Order", backref="return_requests")
    order_item = db.relationship("OrderItem", backref="return_requests")
