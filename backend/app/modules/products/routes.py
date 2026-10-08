import re
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.core.decorators import active_supplier_required
from app.extensions import db
from app.modules.brands.models import Brand
from app.modules.categories.models import Category
from app.utils.response import error_response, success_response
from .models import Product
from .schemas import ProductCreateSchema
from .services import ProductService, get_product, update_product, delete_product


def generate_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


products_bp = Blueprint("products", __name__, url_prefix="/api/products")


@products_bp.get("/health")
def health():
    return jsonify({"success": True, "message": "Products module working."})


@products_bp.post("/")
@active_supplier_required
def create():
    data = request.get_json(silent=True) or {}
    errors = ProductCreateSchema().validate(data)
    if errors:
        return error_response(message=errors, status_code=400)
    try:
        product = ProductService.create(data, int(get_jwt_identity()))
    except ValueError as exc:
        db.session.rollback()
        return error_response(message=str(exc), status_code=400)
    return success_response(
        message="Product created successfully.",
        data={"id": product.id, "name": product.name, "slug": product.slug},
        status_code=201,
    )


@products_bp.get("/")
def list_products():
    return success_response(
        data=ProductService.search(
            search=request.args.get("search"),
            category_id=request.args.get("category_id", type=int),
            min_price=request.args.get("min_price", type=float),
            max_price=request.args.get("max_price", type=float),
            sort=request.args.get("sort"),
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 10, type=int),
        )
    )


@products_bp.get("/supplier")
@active_supplier_required
def supplier_products():
    account_id = int(get_jwt_identity())
    return success_response(
        data=(
            ProductService.catalog_for_supplier(account_id)
            if hasattr(ProductService, "catalog_for_supplier")
            else [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "slug": p.slug,
                    "price": float(p.price or 0),
                    "compare_price": (
                        float(p.compare_price) if p.compare_price is not None else None
                    ),
                    "stock": int(p.stock or 0),
                    "status": p.status,
                    "featured": bool(p.is_featured),
                    "category": p.category.name if p.category else "-",
                    "brand": p.brand.name if p.brand else "",
                    "image": p.images[0].image_url if p.images else None,
                    "low_stock_threshold": int(p.low_stock_threshold or 5),
                    "variant_count": len(p.variants),
                }
                for p in Product.query.filter_by(seller_id=account_id)
                .order_by(Product.created_at.desc())
                .all()
            ]
        )
    )


@products_bp.get("/supplier/<int:product_id>")
@active_supplier_required
def supplier_product_detail(product_id):
    product = Product.query.filter_by(
        id=product_id, seller_id=int(get_jwt_identity())
    ).first()
    if not product:
        return error_response(message="Product not found.", status_code=404)
    return success_response(data=ProductService.serialize_supplier(product))


@products_bp.get("/<int:product_id>")
def product_detail(product_id):
    product = get_product(product_id)
    if not product or product.status != "ACTIVE":
        return error_response(message="Product not found.", status_code=404)
    return success_response(data=ProductService.serialize_public(product))


@products_bp.put("/<int:product_id>")
@active_supplier_required
def update(product_id):
    product = Product.query.filter_by(
        id=product_id, seller_id=int(get_jwt_identity())
    ).first()
    if not product:
        return error_response(message="Product not found.", status_code=404)
    try:
        update_product(product, request.get_json(silent=True) or {})
    except ValueError as exc:
        db.session.rollback()
        return error_response(message=str(exc), status_code=400)
    return success_response(
        message="Product updated.",
        data=ProductService.serialize_supplier(product),
    )


@products_bp.delete("/<int:product_id>")
@active_supplier_required
def delete(product_id):
    product = (
        Product.query.filter_by(id=product_id, seller_id=int(get_jwt_identity()))
        .with_for_update()
        .first()
    )
    if not product:
        return error_response(message="Product not found.", status_code=404)
    try:
        delete_product(product)
    except ValueError as exc:
        db.session.rollback()
        return error_response(message=str(exc), status_code=409)
    except IntegrityError:
        db.session.rollback()
        return error_response(
            message="Product could not be deleted because another record still references it.",
            status_code=409,
        )
    return success_response(message="Product deleted permanently.")


@products_bp.post("/categories/")
@active_supplier_required
def create_supplier_category():
    name = str((request.get_json(silent=True) or {}).get("name", "")).strip()
    if not name:
        return error_response(message="Category name is required.", status_code=400)
    if Category.query.filter(func.lower(Category.name) == name.lower()).first():
        return error_response(message="Category already exists.", status_code=409)
    category = Category(name=name, slug=generate_slug(name))
    db.session.add(category)
    db.session.commit()
    return success_response(
        data={"id": category.id, "name": category.name},
        message="Category created.",
        status_code=201,
    )


@products_bp.delete("/categories/<int:category_id>/")
@active_supplier_required
def delete_supplier_category(category_id):
    return error_response(
        message="Categories are shared catalog data and cannot be deleted from the supplier portal.",
        status_code=403,
    )


@products_bp.post("/brands/")
@active_supplier_required
def create_supplier_brand():
    name = str((request.get_json(silent=True) or {}).get("name", "")).strip()
    if not name:
        return error_response(message="Brand name is required.", status_code=400)
    if Brand.query.filter(func.lower(Brand.name) == name.lower()).first():
        return error_response(message="Brand already exists.", status_code=409)
    brand = Brand(name=name, slug=generate_slug(name))
    db.session.add(brand)
    db.session.commit()
    return success_response(
        data={"id": brand.id, "name": brand.name},
        message="Brand created.",
        status_code=201,
    )


@products_bp.delete("/brands/<int:brand_id>/")
@active_supplier_required
def delete_supplier_brand(brand_id):
    return error_response(
        message="Brands are shared catalog data and cannot be deleted from the supplier portal.",
        status_code=403,
    )
