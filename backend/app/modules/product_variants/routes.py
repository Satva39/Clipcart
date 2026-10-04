from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.core.decorators import active_supplier_required
from app.extensions import db
from app.modules.inventory.models import InventoryLog
from app.modules.products.models import Product
from app.utils.response import success_response, error_response
from .models import ProductVariant
from sqlalchemy.orm import selectinload

product_variants_bp = Blueprint(
    "product_variants", __name__, url_prefix="/api/product-variants"
)


def _normalize_options(item):
    raw = item.get("options") or item.get("option_values") or []
    if isinstance(raw, dict):
        raw = [{"name": k, "value": v} for k, v in raw.items()]
    if not isinstance(raw, list):
        raise ValueError("Variant options must be an array or object.")
    normalized = []
    seen = set()
    for option in raw:
        if not isinstance(option, dict):
            continue
        name = str(option.get("name", "")).strip()
        value = str(option.get("value", "")).strip()
        if not name or not value:
            continue
        key = name.casefold()
        if key in seen:
            raise ValueError(f"Duplicate variant option '{name}'.")
        seen.add(key)
        normalized.append({"name": name, "value": value})
    if not normalized:
        raise ValueError("Each variant must contain at least one option.")
    normalized.sort(key=lambda x: x["name"].casefold())
    return normalized


def _combination_key(options):
    if isinstance(options, dict):
        options = [{"name": key, "value": value} for key, value in options.items()]
    if not isinstance(options, list):
        options = []

    normalized = []
    for item in options:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip().casefold()
        value = str(item.get("value", "")).strip().casefold()
        if name and value:
            normalized.append((name, value))

    normalized.sort(key=lambda pair: pair[0])
    return tuple(normalized)


def _serialize(v):
    return {
        "id": v.id,
        "product_id": v.product_id,
        "name": v.name,
        "value": v.value,
        "option_values": v.option_values
        or ({v.name: v.value} if v.name and v.value else {}),
        "sku": v.sku,
        "price": float(v.price or 0),
        "compare_price": (
            float(v.compare_price) if v.compare_price is not None else None
        ),
        "stock": int(v.stock or 0),
        "is_active": bool(getattr(v, "is_active", True)),
        "images": [
            {"id": img.id, "image_url": img.image_url, "is_thumbnail": img.is_thumbnail}
            for img in v.images
        ],
    }


@product_variants_bp.post("/product/<int:product_id>")
@active_supplier_required
def create_product_variants(product_id):
    supplier_id = int(get_jwt_identity())
    product = Product.query.filter_by(id=product_id, seller_id=supplier_id).first()
    if not product:
        return error_response(
            message="Product not found or access denied.", status_code=404
        )
    variants = (request.get_json(silent=True) or {}).get("variants", [])
    if not isinstance(variants, list) or not variants:
        return error_response(
            message="variants must be a non-empty array.", status_code=400
        )
    existing_keys = set()
    for v in ProductVariant.query.filter_by(product_id=product_id).all():
        existing_options = v.option_values or (
            [{"name": v.name, "value": v.value}] if v.name and v.value else []
        )
        key = _combination_key(existing_options)
        if key:
            existing_keys.add(key)
    created = []
    batch_keys = set()
    batch_skus = set()
    for item in variants:
        if not isinstance(item, dict):
            db.session.rollback()
            return error_response(
                message="Each variant must be a valid object.",
                status_code=400,
            )
        try:
            options = _normalize_options(item)
            key = _combination_key(options)
        except ValueError as exc:
            db.session.rollback()
            return error_response(message=str(exc), status_code=400)
        if key in existing_keys or key in batch_keys:
            db.session.rollback()
            return error_response(
                message="Duplicate variant combination. Each option combination must be unique.",
                status_code=409,
            )
        batch_keys.add(key)
        sku = str(item.get("sku", "")).strip()
        if not sku:
            return error_response(message="Variant SKU is required.", status_code=400)
        if sku in batch_skus or ProductVariant.query.filter_by(sku=sku).first():
            db.session.rollback()
            return error_response(
                message=f"Variant SKU '{sku}' already exists.", status_code=409
            )
        batch_skus.add(sku)
        try:
            price = float(item.get("price", product.price or 0))
            compare_price = item.get("compare_price")
            compare_price = (
                None if compare_price in (None, "") else float(compare_price)
            )
            stock = int(item.get("stock", 0))
        except (TypeError, ValueError):
            db.session.rollback()
            return error_response(
                message="Variant price, compare price and stock must be valid numbers.",
                status_code=400,
            )
        if (
            price < 0
            or stock < 0
            or (compare_price is not None and compare_price < price)
        ):
            return error_response(
                message="Variant price/stock values are invalid.", status_code=400
            )
        option_values = {x["name"]: x["value"] for x in options}
        variant = ProductVariant(
            product_id=product_id,
            name=" / ".join(x["name"] for x in options),
            value=" / ".join(x["value"] for x in options),
            option_values=option_values,
            sku=sku,
            price=price,
            compare_price=compare_price,
            stock=stock,
            is_active=bool(item.get("is_active", True)),
        )
        db.session.add(variant)
        created.append(variant)
    try:
        product.stock = sum(
            int(v.stock or 0) for v in product.variants if getattr(v, "is_active", True)
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return success_response(
        data=[_serialize(v) for v in created],
        message="Product variants created.",
        status_code=201,
    )


@product_variants_bp.get("/product/<int:product_id>")
@active_supplier_required
def get_product_variants(product_id):
    product = Product.query.filter_by(
        id=product_id, seller_id=int(get_jwt_identity())
    ).first()
    if not product:
        return error_response(
            message="Product not found or access denied.", status_code=404
        )
    return success_response(
        data=[
            _serialize(v)
            for v in ProductVariant.query.options(selectinload(ProductVariant.images))
            .filter_by(product_id=product_id)
            .order_by(ProductVariant.id.asc())
            .all()
        ]
    )


@product_variants_bp.put("/<int:variant_id>")
@active_supplier_required
def update_product_variant(variant_id):
    variant = ProductVariant.query.get(variant_id)
    if not variant:
        return error_response(message="Variant not found.", status_code=404)
    product = Product.query.filter_by(
        id=variant.product_id, seller_id=int(get_jwt_identity())
    ).first()
    if not product:
        return error_response(message="Unauthorized.", status_code=403)
    data = request.get_json(silent=True) or {}
    try:
        options = (
            _normalize_options(data)
            if ("options" in data or "option_values" in data)
            else [
                {"name": n, "value": val}
                for n, val in (variant.option_values or {}).items()
            ]
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    key = _combination_key(options)
    for other in ProductVariant.query.filter(
        ProductVariant.product_id == product.id, ProductVariant.id != variant.id
    ).all():
        other_options = other.option_values or (
            [{"name": other.name, "value": other.value}]
            if other.name and other.value
            else []
        )
        other_key = _combination_key(other_options)
        if other_key and other_key == key:
            return error_response(
                message="Duplicate variant combination.", status_code=409
            )
    sku = str(data.get("sku", variant.sku)).strip()
    if not sku:
        return error_response(message="Variant SKU is required.", status_code=400)
    if ProductVariant.query.filter(
        ProductVariant.sku == sku, ProductVariant.id != variant.id
    ).first():
        return error_response(
            message=f"Variant SKU '{sku}' already exists.", status_code=409
        )
    try:
        price = float(data.get("price", variant.price or product.price or 0))
        compare_price = data.get("compare_price", variant.compare_price)
        compare_price = None if compare_price in (None, "") else float(compare_price)
        new_stock = int(data.get("stock", variant.stock or 0))
    except (TypeError, ValueError):
        return error_response(
            message="Variant values must be valid numbers.", status_code=400
        )
    if min(price, new_stock) < 0 or (
        compare_price is not None and compare_price < price
    ):
        return error_response(
            message="Variant price/stock values are invalid.", status_code=400
        )
    old_stock = int(variant.stock or 0)
    variant.name = " / ".join(x["name"] for x in options)
    variant.value = " / ".join(x["value"] for x in options)
    variant.option_values = {x["name"]: x["value"] for x in options}
    variant.sku = sku
    variant.price = price
    variant.compare_price = compare_price
    variant.stock = new_stock
    if "is_active" in data:
        variant.is_active = bool(data["is_active"])
    if new_stock != old_stock:
        db.session.add(
            InventoryLog(
                product_id=variant.product_id,
                variant_id=variant.id,
                change=new_stock - old_stock,
                reason="VARIANT_UPDATED",
            )
        )
    product.stock = sum(
        int(v.stock or 0) for v in product.variants if getattr(v, "is_active", True)
    )
    db.session.commit()
    return success_response(message="Variant updated.", data=_serialize(variant))


@product_variants_bp.delete("/<int:variant_id>")
@active_supplier_required
def delete_product_variant(variant_id):
    variant = ProductVariant.query.get(variant_id)
    if not variant:
        return error_response(message="Variant not found.", status_code=404)
    product = Product.query.filter_by(
        id=variant.product_id, seller_id=int(get_jwt_identity())
    ).first()
    if not product:
        return error_response(message="Unauthorized.", status_code=403)
    db.session.delete(variant)
    db.session.flush()
    product.stock = sum(
        int(v.stock or 0)
        for v in product.variants
        if v.id != variant.id and getattr(v, "is_active", True)
    )
    db.session.commit()
    return success_response(message="Variant deleted.")
