from slugify import slugify
from sqlalchemy import or_

from app.extensions import db
from app.modules.categories.repository import CategoryRepository
from app.modules.order_items.models import OrderItem
from app.modules.cart.models import CartItem
from app.modules.wishlist.models import WishlistItem
from app.modules.brands.repository import BrandRepository
from app.modules.inventory.models import InventoryLog
from app.modules.stock_alerts.services import StockAlertService
from app.modules.stock_alerts.models import StockAlertSubscription
from app.modules.reviews.models import Review
from .models import Product
from .repository import ProductRepository


class ProductService:
    @staticmethod
    def search(
        search=None,
        category_id=None,
        min_price=None,
        max_price=None,
        sort=None,
        page=1,
        per_page=10,
    ):
        query = Product.query.filter(Product.status == "ACTIVE")
        if search:
            term = search.strip()
            if term:
                query = query.filter(
                    or_(Product.name.ilike(f"%{term}%"), Product.sku.ilike(f"%{term}%"))
                )
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        order_map = {
            "price_asc": Product.price.asc(),
            "price_desc": Product.price.desc(),
            "name": Product.name.asc(),
            "stock": Product.stock.desc(),
        }
        query = query.order_by(order_map.get(sort, Product.created_at.desc()))
        pagination = query.paginate(
            page=max(1, page), per_page=min(max(1, per_page), 100), error_out=False
        )
        return {
            "products": [ProductService.serialize_public(p) for p in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages,
                "total": pagination.total,
            },
        }

    @staticmethod
    def serialize_public(product):
        return {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "price": float(product.price or 0),
            "compare_price": (
                float(product.compare_price)
                if product.compare_price is not None
                else None
            ),
            "stock": int(product.stock or 0),
            "shipping": {
                "weight_kg": (
                    float(product.shipping_weight_kg)
                    if product.shipping_weight_kg is not None
                    else None
                ),
                "length_cm": (
                    float(product.shipping_length_cm)
                    if product.shipping_length_cm is not None
                    else None
                ),
                "width_cm": (
                    float(product.shipping_width_cm)
                    if product.shipping_width_cm is not None
                    else None
                ),
                "height_cm": (
                    float(product.shipping_height_cm)
                    if product.shipping_height_cm is not None
                    else None
                ),
            },
            "category": product.category.name if product.category else None,
            "featured": bool(product.is_featured),
            "brand": product.brand.name if product.brand else None,
            "highlights": product.highlights or [],
            "specifications": product.specifications or {},
        }

    @staticmethod
    def serialize_supplier(product):
        return {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "highlights": product.highlights or [],
            "specifications": product.specifications or {},
            "price": float(product.price or 0),
            "compare_price": (
                float(product.compare_price)
                if product.compare_price is not None
                else None
            ),
            "stock": int(product.stock or 0),
            "shipping_weight_kg": (
                float(product.shipping_weight_kg)
                if product.shipping_weight_kg is not None
                else None
            ),
            "shipping_length_cm": (
                float(product.shipping_length_cm)
                if product.shipping_length_cm is not None
                else None
            ),
            "shipping_width_cm": (
                float(product.shipping_width_cm)
                if product.shipping_width_cm is not None
                else None
            ),
            "shipping_height_cm": (
                float(product.shipping_height_cm)
                if product.shipping_height_cm is not None
                else None
            ),
            "low_stock_threshold": int(product.low_stock_threshold or 5),
            "sku": product.sku,
            "status": product.status,
            "is_featured": bool(product.is_featured),
            "category_id": product.category_id,
            "category": product.category.name if product.category else "",
            "brand_id": product.brand_id,
            "brand": product.brand.name if product.brand else "",
            "images": [
                {
                    "id": img.id,
                    "image_url": img.image_url,
                    "sort_order": img.sort_order,
                    "is_thumbnail": img.is_thumbnail,
                    "variant_id": img.variant_id,
                }
                for img in product.images
            ],
            "variants": [
                {
                    "id": v.id,
                    "name": v.name,
                    "value": v.value,
                    "option_values": v.option_values or {},
                    "sku": v.sku,
                    "price": float(v.price or 0),
                    "compare_price": (
                        float(v.compare_price) if v.compare_price is not None else None
                    ),
                    "stock": int(v.stock or 0),
                    "is_active": bool(getattr(v, "is_active", True)),
                    "images": [
                        {
                            "id": img.id,
                            "image_url": img.image_url,
                            "is_thumbnail": img.is_thumbnail,
                        }
                        for img in v.images
                    ],
                }
                for v in product.variants
            ],
        }

    @staticmethod
    def _unique_slug(name):
        base_slug = slugify(name) or "product"
        slug = base_slug
        counter = 2
        while ProductRepository.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    @staticmethod
    def create(data, seller_id):
        category = CategoryRepository.get_by_id(data["category_id"])
        if not category:
            raise ValueError("Category does not exist.")
        brand_id = data.get("brand_id")
        if brand_id is not None and not BrandRepository.get_by_id(brand_id):
            raise ValueError("Brand does not exist.")
        sku = str(data.get("sku", "")).strip()
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        if not name or len(name) > 255:
            raise ValueError(
                "Product name is required and must be 255 characters or fewer."
            )
        if not description:
            raise ValueError("Product description is required.")
        if not sku:
            raise ValueError("SKU is required.")
        if ProductRepository.get_by_sku(sku):
            raise ValueError(f"SKU '{sku}' already exists. Please use a unique SKU.")
        try:
            price = float(data.get("price"))
        except (TypeError, ValueError):
            raise ValueError("Price must be a valid number.")
        try:
            stock = int(data.get("stock", 0))
            threshold = int(data.get("low_stock_threshold", 5))
        except (TypeError, ValueError):
            raise ValueError("Stock and low-stock threshold must be whole numbers.")
        if price < 0 or stock < 0 or threshold < 0:
            raise ValueError("Price, stock and low-stock threshold cannot be negative.")
        compare_price = data.get("compare_price")
        if compare_price not in (None, "") and float(compare_price) < price:
            raise ValueError(
                "Compare/MRP price cannot be lower than the selling price."
            )
        status = str(data.get("status", "ACTIVE")).upper()
        if status not in {"ACTIVE", "INACTIVE"}:
            raise ValueError("Invalid product status.")
        shipping_values = {}
        for field in (
            "shipping_weight_kg",
            "shipping_length_cm",
            "shipping_width_cm",
            "shipping_height_cm",
        ):
            raw = data.get(field)
            if raw in (None, ""):
                shipping_values[field] = None
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                raise ValueError(f"{field} must be a valid number.")
            minimum = 0.0001 if field == "shipping_weight_kg" else 0.5
            if value < minimum:
                raise ValueError(f"{field} must be greater than {minimum}.")
            shipping_values[field] = value
        product = Product(
            seller_id=seller_id,
            category_id=data["category_id"],
            brand_id=data.get("brand_id"),
            name=name,
            slug=ProductService._unique_slug(name),
            description=description,
            highlights=data.get("highlights") or [],
            specifications=data.get("specifications") or {},
            price=price,
            compare_price=compare_price,
            stock=stock,
            shipping_weight_kg=shipping_values["shipping_weight_kg"],
            shipping_length_cm=shipping_values["shipping_length_cm"],
            shipping_width_cm=shipping_values["shipping_width_cm"],
            shipping_height_cm=shipping_values["shipping_height_cm"],
            low_stock_threshold=threshold,
            sku=sku,
            status=status,
            is_featured=bool(data.get("is_featured", False)),
        )
        return ProductRepository.create(product)


def create_product(**kwargs):
    product = Product(**kwargs)
    db.session.add(product)
    db.session.commit()
    return product


def get_all_products():
    return Product.query.all()


def get_product(product_id):
    return Product.query.get(product_id)


def update_product(product, data):
    allowed = {
        "name",
        "category_id",
        "brand_id",
        "description",
        "highlights",
        "specifications",
        "price",
        "compare_price",
        "stock",
        "low_stock_threshold",
        "shipping_weight_kg",
        "shipping_length_cm",
        "shipping_width_cm",
        "shipping_height_cm",
        "sku",
        "status",
        "is_featured",
    }
    unknown = set(data) - allowed
    if unknown:
        raise ValueError("Unsupported product fields: " + ", ".join(sorted(unknown)))
    name = str(data.get("name", product.name)).strip()
    if not name:
        raise ValueError("Product name is required.")
    if "category_id" in data and not CategoryRepository.get_by_id(data["category_id"]):
        raise ValueError("Category does not exist.")
    if (
        "brand_id" in data
        and data["brand_id"] is not None
        and not BrandRepository.get_by_id(data["brand_id"])
    ):
        raise ValueError("Brand does not exist.")
    for field in (
        "shipping_weight_kg",
        "shipping_length_cm",
        "shipping_width_cm",
        "shipping_height_cm",
    ):
        if field not in data:
            continue
        raw = data.get(field)
        if raw in (None, ""):
            data[field] = None
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a valid number.")
        minimum = 0.0001 if field == "shipping_weight_kg" else 0.5
        if value < minimum:
            raise ValueError(f"{field} must be greater than {minimum}.")
        data[field] = value

    if "sku" in data:
        sku = str(data["sku"]).strip()
        if not sku:
            raise ValueError("SKU is required.")
        if Product.query.filter(Product.sku == sku, Product.id != product.id).first():
            raise ValueError(f"SKU '{sku}' already exists.")
        data["sku"] = sku
    if "price" in data:
        try:
            price = float(data["price"])
        except (TypeError, ValueError):
            raise ValueError("Price must be a valid number.")
        if price < 0:
            raise ValueError("Price cannot be negative.")
        data["price"] = price
    price = float(data.get("price", product.price or 0))
    compare_price = data.get("compare_price", product.compare_price)
    if compare_price not in (None, ""):
        try:
            compare_price = float(compare_price)
        except (TypeError, ValueError):
            raise ValueError("Compare/MRP price must be a valid number.")
        if compare_price < price:
            raise ValueError(
                "Compare/MRP price cannot be lower than the selling price."
            )
    if "stock" in data:
        try:
            data["stock"] = int(data["stock"])
        except (TypeError, ValueError):
            raise ValueError("Stock must be a whole number.")
        if data["stock"] < 0:
            raise ValueError("Stock cannot go below zero.")
    if "low_stock_threshold" in data:
        try:
            data["low_stock_threshold"] = int(data["low_stock_threshold"])
        except (TypeError, ValueError):
            raise ValueError("Low-stock threshold must be a whole number.")
        if data["low_stock_threshold"] < 0:
            raise ValueError("Low-stock threshold cannot be negative.")
    status = str(data.get("status", product.status)).upper()
    if status not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("Invalid product status.")
    data["status"] = status
    old_stock = int(product.stock or 0)
    product.name = name
    for key, value in data.items():
        setattr(product, key, value)
    if product.variants:
        product.stock = sum(
            int(variant.stock or 0)
            for variant in product.variants
            if getattr(variant, "is_active", True)
        )
    new_stock = int(product.stock or 0)
    if new_stock != old_stock:
        db.session.add(
            InventoryLog(
                product_id=product.id,
                variant_id=None,
                change=new_stock - old_stock,
                reason="PRODUCT_UPDATED",
            )
        )
    db.session.commit()
    if new_stock > old_stock:
        try:
            StockAlertService.notify_available(product.id, None)
        except Exception:
            db.session.rollback()
    return product


def delete_product(product):
    """Permanently delete never-ordered products; preserve products referenced by history."""
    has_order_history = OrderItem.query.filter_by(product_id=product.id).first() is not None
    if has_order_history:
        raise ValueError(
            "This product is linked to existing order history and cannot be permanently deleted. Deactivate it instead."
        )

    if Review.query.filter_by(product_id=product.id).first() is not None:
        raise ValueError(
            "This product has customer reviews and cannot be permanently deleted. Deactivate it instead."
        )

    CartItem.query.filter_by(product_id=product.id).delete(synchronize_session=False)
    WishlistItem.query.filter_by(product_id=product.id).delete(synchronize_session=False)
    InventoryLog.query.filter_by(product_id=product.id).delete(synchronize_session=False)
    StockAlertSubscription.query.filter_by(product_id=product.id).delete(synchronize_session=False)

    db.session.delete(product)
    db.session.commit()
    return product
