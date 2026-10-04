from sqlalchemy import Numeric
from app.extensions import db
from app.modules.brands.models import Brand
from app.shared.models.base_model import BaseModel


class Product(BaseModel):
    __tablename__ = "products"
    __table_args__ = (
        db.CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
    )

    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=False,
    )

    name = db.Column(
        db.String(255),
        nullable=False,
    )

    slug = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
    )

    description = db.Column(
        db.Text,
    )

    highlights = db.Column(db.JSON, nullable=True)

    specifications = db.Column(db.JSON, nullable=True)

    price = db.Column(
        Numeric(10, 2),
        nullable=False,
    )

    compare_price = db.Column(
        Numeric(10, 2),
    )

    stock = db.Column(
        db.Integer,
        default=0,
    )

    # Physical package profile required for real courier fulfillment. These
    # values describe one sellable package unit and are intentionally nullable
    # so existing products remain valid until a supplier is ready to ship them.
    shipping_weight_kg = db.Column(db.Numeric(10, 3), nullable=True)
    shipping_length_cm = db.Column(db.Numeric(10, 2), nullable=True)
    shipping_width_cm = db.Column(db.Numeric(10, 2), nullable=True)
    shipping_height_cm = db.Column(db.Numeric(10, 2), nullable=True)

    low_stock_threshold = db.Column(db.Integer, default=5, nullable=False)

    sku = db.Column(
        db.String(100),
        unique=True,
    )

    status = db.Column(
        db.String(20),
        default="ACTIVE",
    )

    is_featured = db.Column(
        db.Boolean,
        default=False,
    )

    brand_id = db.Column(
        db.Integer,
        db.ForeignKey("brands.id"),
        nullable=True,
        index=True,
    )

    brand = db.relationship(
        "Brand",
        backref="products",
    )

    seller = db.relationship(
        "Account",
        back_populates="products",
    )

    category = db.relationship(
        "Category",
        backref="products",
    )

    images = db.relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )

    variants = db.relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )
