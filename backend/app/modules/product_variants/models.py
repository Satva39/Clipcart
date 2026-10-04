from app.extensions import db
from app.shared.models.base_model import BaseModel


class ProductVariant(BaseModel):

    __tablename__ = "product_variants"
    __table_args__ = (
        db.CheckConstraint(
            "stock >= 0",
            name="ck_product_variants_stock_nonnegative",
        ),
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
    )

    name = db.Column(
        db.String(100),
        nullable=False,
    )

    value = db.Column(
        db.String(500),
        nullable=False,
    )

    option_values = db.Column(db.JSON, nullable=True)

    sku = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
    )

    price = db.Column(
        db.Numeric(10, 2),
        nullable=False,
    )

    compare_price = db.Column(db.Numeric(10, 2), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    stock = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    product = db.relationship(
        "Product",
        back_populates="variants",
    )

    images = db.relationship(
        "ProductImage",
        back_populates="variant",
        cascade="all, delete-orphan",
    )
