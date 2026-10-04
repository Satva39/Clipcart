from app.extensions import db
from app.shared.models.base_model import BaseModel


class ProductImage(BaseModel):

    __tablename__ = "product_images"

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
    )

    variant_id = db.Column(
        db.Integer,
        db.ForeignKey("product_variants.id"),
        nullable=True,
    )

    image_url = db.Column(
        db.String(500),
        nullable=False,
    )

    public_id = db.Column(
        db.String(255),
        nullable=False,
    )

    sort_order = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    is_thumbnail = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
    )

    product = db.relationship(
        "Product",
        back_populates="images",
    )

    variant = db.relationship(
        "ProductVariant",
        back_populates="images",
    )