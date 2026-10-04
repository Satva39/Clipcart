from app.extensions import db
from app.shared.models.base_model import BaseModel


class InventoryLog(BaseModel):

    __tablename__ = "inventory_logs"

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=True,
    )

    variant_id = db.Column(
        db.Integer,
        db.ForeignKey("product_variants.id"),
        nullable=True,
    )

    change = db.Column(
        db.Integer,
        nullable=False,
    )

    reason = db.Column(
        db.String(255),
        nullable=False,
    )

    product = db.relationship(
        "Product",
        backref="inventory_logs",
    )

    variant = db.relationship(
        "ProductVariant",
        backref="inventory_logs",
    )