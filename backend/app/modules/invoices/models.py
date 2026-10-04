from app.extensions import db
from app.shared.models.base_model import BaseModel


class Invoice(BaseModel):
    __tablename__ = "invoices"

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    invoice_number = db.Column(db.String(80), unique=True, nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="PENDING")
    generated_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship(
        "Order",
        backref=db.backref("invoice", uselist=False),
    )
