from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from app.core.decorators import active_supplier_required
from app.extensions import db
from app.modules.notifications.enums import NotificationType
from app.modules.notifications.services import NotificationService
from app.modules.products.models import Product
from app.modules.product_variants.models import ProductVariant
from app.utils.response import success_response, error_response
from .models import InventoryLog

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")


def _stock_status(stock, threshold):
    stock = int(stock or 0)
    threshold = int(threshold or 5)
    if stock <= 0:
        return "OUT_OF_STOCK"
    if stock <= threshold:
        return "LOW_STOCK"
    return "IN_STOCK"


def _notify_low_stock(supplier_id, product, variant=None):
    stock = int(variant.stock if variant else product.stock or 0)
    threshold = int(product.low_stock_threshold or 5)
    if stock <= threshold:
        label = product.name + (f" ({variant.value})" if variant else "")
        title = "Out of stock" if stock == 0 else "Low stock alert"
        message = f"{label} has {stock} unit{'s' if stock != 1 else ''} remaining."
        NotificationService.create(
            supplier_id,
            title,
            message,
            NotificationType.SYSTEM,
            dedupe_key=f"supplier-stock:{supplier_id}:{product.id}:{variant.id if variant else 0}:{stock}",
        )


@inventory_bp.get("/supplier")
@active_supplier_required
def supplier_inventory():
    supplier_id = int(get_jwt_identity())
    products = (
        Product.query.options(
            selectinload(Product.category),
            selectinload(Product.images),
            selectinload(Product.variants),
        )
        .filter_by(seller_id=supplier_id)
        .order_by(Product.created_at.desc())
        .all()
    )
    data = []
    for product in products:
        variants = [
            {
                "id": v.id,
                "name": v.name,
                "value": v.value,
                "option_values": v.option_values or {},
                "sku": v.sku,
                "stock": int(v.stock or 0),
                "status": _stock_status(v.stock, product.low_stock_threshold),
                "is_active": bool(getattr(v, "is_active", True)),
            }
            for v in product.variants
        ]
        product_status = (
            _stock_status(product.stock, product.low_stock_threshold)
            if not variants
            else (
                "OUT_OF_STOCK"
                if variants and all(v["stock"] == 0 for v in variants)
                else (
                    "LOW_STOCK"
                    if any(
                        _stock_status(v["stock"], product.low_stock_threshold)
                        == "LOW_STOCK"
                        for v in variants
                    )
                    else "IN_STOCK"
                )
            )
        )
        data.append(
            {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "category": product.category.name if product.category else "-",
                "stock": int(product.stock or 0),
                "price": float(product.price or 0),
                "status": product.status,
                "stock_status": product_status,
                "low_stock_threshold": int(product.low_stock_threshold or 5),
                "image": product.images[0].image_url if product.images else None,
                "variants": variants,
            }
        )
    return success_response(data=data)


@inventory_bp.get("/supplier/<int:product_id>/history")
@active_supplier_required
def inventory_history(product_id):
    supplier_id = int(get_jwt_identity())
    if not Product.query.filter_by(id=product_id, seller_id=supplier_id).first():
        return error_response(message="Product not found.", status_code=404)
    logs = (
        InventoryLog.query.options(joinedload(InventoryLog.variant))
        .filter_by(product_id=product_id)
        .order_by(InventoryLog.created_at.desc())
        .limit(200)
        .all()
    )
    return success_response(
        data=[
            {
                "id": l.id,
                "variant_id": l.variant_id,
                "variant": l.variant.value if l.variant else None,
                "change": l.change,
                "reason": l.reason,
                "created_at": l.created_at,
            }
            for l in logs
        ]
    )


@inventory_bp.put("/supplier/<int:product_id>/adjust")
@active_supplier_required
def adjust_inventory(product_id):
    supplier_id = int(get_jwt_identity())
    product = Product.query.filter_by(id=product_id, seller_id=supplier_id).first()
    if not product:
        return error_response(message="Product not found.", status_code=404)
    data = request.get_json(silent=True) or {}
    variant_id = data.get("variant_id")
    variant = None
    target = product
    if variant_id is not None:
        try:
            variant_id = int(variant_id)
        except (TypeError, ValueError):
            return error_response(message="Invalid variant ID.", status_code=400)
        variant = (
            ProductVariant.query.filter_by(id=variant_id, product_id=product.id)
            .with_for_update()
            .first()
        )
        if not variant:
            return error_response(message="Variant not found.", status_code=404)
        target = variant
    else:
        target = (
            Product.query.filter_by(id=product.id, seller_id=supplier_id)
            .with_for_update()
            .first()
        )

    mode = str(data.get("mode", "adjust")).lower()
    try:
        amount = int(data.get("amount", data.get("change", 0)))
    except (TypeError, ValueError):
        return error_response(
            message="Stock amount must be a whole number.", status_code=400
        )
    old_stock = int(target.stock or 0)
    if mode == "set":
        new_stock = amount
        change = new_stock - old_stock
    elif mode == "adjust":
        change = amount
        new_stock = old_stock + change
    else:
        return error_response(
            message="Mode must be 'adjust' or 'set'.", status_code=400
        )
    if new_stock < 0:
        return error_response(message="Stock cannot go below zero.", status_code=400)
    if new_stock == old_stock:
        return error_response(
            message="Stock is already at that quantity.", status_code=400
        )
    target.stock = new_stock
    if variant is not None:
        active_variants = [v for v in product.variants if getattr(v, "is_active", True)]
        product.stock = sum(int(v.stock or 0) for v in active_variants)
    reason = (
        str(data.get("reason", "MANUAL_ADJUSTMENT")).strip()[:255]
        or "MANUAL_ADJUSTMENT"
    )
    db.session.add(
        InventoryLog(
            product_id=product.id,
            variant_id=variant.id if variant else None,
            change=change,
            reason=reason,
        )
    )
    db.session.commit()
    try:
        _notify_low_stock(supplier_id, product, variant)
    except Exception:
        db.session.rollback()
    return success_response(
        message="Inventory updated successfully.",
        data={
            "product_id": product.id,
            "variant_id": variant.id if variant else None,
            "stock": new_stock,
            "change": change,
            "reason": reason,
        },
    )


@inventory_bp.get("/supplier/alerts")
@active_supplier_required
def inventory_alerts():
    supplier_id = int(get_jwt_identity())
    products = (
        Product.query.options(selectinload(Product.variants))
        .filter_by(seller_id=supplier_id)
        .all()
    )
    low = []
    out = []
    for product in products:
        if product.variants:
            for v in product.variants:
                if not getattr(v, "is_active", True):
                    continue
                status = _stock_status(v.stock, product.low_stock_threshold)
                payload = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "variant_id": v.id,
                    "variant": v.value,
                    "stock": int(v.stock or 0),
                    "threshold": int(product.low_stock_threshold or 5),
                }
                if status == "OUT_OF_STOCK":
                    out.append(payload)
                elif status == "LOW_STOCK":
                    low.append(payload)
        else:
            status = _stock_status(product.stock, product.low_stock_threshold)
            payload = {
                "product_id": product.id,
                "product_name": product.name,
                "variant_id": None,
                "variant": None,
                "stock": int(product.stock or 0),
                "threshold": int(product.low_stock_threshold or 5),
            }
            if status == "OUT_OF_STOCK":
                out.append(payload)
            elif status == "LOW_STOCK":
                low.append(payload)
    return success_response(data={"low_stock": low, "out_of_stock": out})
