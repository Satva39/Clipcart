from flask import Blueprint, make_response, request

from app.utils.response import error_response, success_response

from .services import StoreService, serialize_product

store_bp = Blueprint(
    "store",
    __name__,
    url_prefix="/api/store",
)


@store_bp.get("/home")
def home():
    response_body, status_code = success_response(data=StoreService.get_home_data())

    response = make_response(response_body, status_code)
    response.headers["Cache-Control"] = "no-store, max-age=0"

    return response


@store_bp.get("/products")
def list_products():
    rows = StoreService.get_products()

    return success_response(data=[serialize_product(row) for row in rows])


@store_bp.get("/product/<int:product_id>")
def product_detail_by_id(product_id):
    data = StoreService.get_product_detail(product_id)

    if not data:
        return error_response(
            message="Product not found.",
            status_code=404,
        )

    product = data["product"]
    payload = data["product_payload"]

    return success_response(
        data={
            **payload,
            "seller": ({"name": product.seller.full_name} if product.seller else None),
            "images": [
                {
                    "id": image.id,
                    "url": image.image_url,
                    "primary": image.is_thumbnail,
                    "variant_id": image.variant_id,
                    "sort_order": image.sort_order,
                }
                for image in data["images"]
            ],
            "variants": [
                {
                    "id": variant.id,
                    "name": variant.name,
                    "value": variant.value,
                    "option_values": variant.option_values or {},
                    "is_active": bool(getattr(variant, "is_active", True)),
                    "sku": variant.sku,
                    "price": float(variant.price),
                    "compare_price": (
                        float(variant.compare_price)
                        if variant.compare_price is not None
                        else None
                    ),
                    "stock": int(variant.stock or 0),
                    "images": [
                        {
                            "id": image.id,
                            "url": image.image_url,
                            "primary": image.is_thumbnail,
                        }
                        for image in sorted(
                            variant.images,
                            key=lambda image: image.sort_order,
                        )
                    ],
                }
                for variant in data["variants"]
            ],
            "review_summary": data["review_stats"],
        }
    )


@store_bp.get("/products/<string:slug>")
def product_detail(slug):
    data = StoreService.get_complete_product(slug)

    if not data:
        return error_response(
            message="Product not found.",
            status_code=404,
        )

    product = data["product"]
    payload = serialize_product(product)

    return success_response(
        data={
            **payload,
            "seller": (
                {
                    "name": product.seller.full_name,
                }
                if product.seller
                else None
            ),
            "images": [
                {
                    "id": image.id,
                    "url": image.image_url,
                    "primary": image.is_thumbnail,
                    "variant_id": image.variant_id,
                    "sort_order": image.sort_order,
                }
                for image in data["images"]
            ],
            "variants": [
                {
                    "id": variant.id,
                    "name": variant.name,
                    "value": variant.value,
                    "option_values": variant.option_values or {},
                    "is_active": bool(getattr(variant, "is_active", True)),
                    "sku": variant.sku,
                    "price": float(variant.price),
                    "compare_price": (
                        float(variant.compare_price)
                        if variant.compare_price is not None
                        else None
                    ),
                    "stock": int(variant.stock or 0),
                    "images": [
                        {
                            "id": image.id,
                            "url": image.image_url,
                            "primary": image.is_thumbnail,
                        }
                        for image in sorted(
                            variant.images,
                            key=lambda image: image.sort_order,
                        )
                    ],
                }
                for variant in data["variants"]
            ],
            "review_summary": data["review_stats"],
        }
    )


@store_bp.get("/categories")
def categories():
    categories = StoreService.get_categories()

    return success_response(
        data=[
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
            }
            for category in categories
        ]
    )


@store_bp.get("/brands")
def brands():
    brands = StoreService.get_brands()

    return success_response(
        data=[
            {
                "id": brand.id,
                "name": brand.name,
                "slug": brand.slug,
                "logo_url": brand.logo_url,
                "description": brand.description,
            }
            for brand in brands
        ]
    )


@store_bp.get("/categories/<string:slug>/products")
def category_products(slug):
    rows = StoreService.get_category_products(slug)

    return success_response(data=[serialize_product(row) for row in rows])


@store_bp.get("/search")
def search_products():
    filters = {
        "q": request.args.get("q"),
        "category": request.args.get("category"),
        "brand": request.args.get("brand"),
        "min_price": request.args.get("min_price", type=float),
        "max_price": request.args.get("max_price", type=float),
        "min_rating": request.args.get("min_rating", type=float),
        "featured": request.args.get("featured") == "true",
        "sort": request.args.get("sort"),
        "page": request.args.get("page", default=1, type=int),
        "limit": request.args.get("limit", default=24, type=int),
        "in_stock": request.args.get("in_stock") == "true",
        "discount": request.args.get("discount") == "true",
        "discount_min": request.args.get("discount_min", type=float),
        "has_variants": request.args.get("has_variants") == "true",
    }

    pagination = StoreService.search(filters)

    return success_response(
        data={
            "products": [serialize_product(row) for row in pagination.items],
            "pagination": {
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


@store_bp.get("/recommendations")
def recommendations():
    raw_viewed = request.args.get("viewed_ids", "")

    viewed_ids = [value.strip() for value in raw_viewed.split(",") if value.strip()]

    products = StoreService.get_recommendations(
        viewed_ids=viewed_ids,
        seed_product_id=request.args.get("seed_product_id"),
        limit=min(
            max(
                request.args.get(
                    "limit",
                    4,
                    type=int,
                ),
                1,
            ),
            4,
        ),
    )

    return success_response(data=products)


@store_bp.get("/settings")
def public_settings():
    from app.modules.admin.services import PlatformSettingsService

    return success_response(data=PlatformSettingsService.public_settings())


@store_bp.get("/banners")
def public_banners():
    from app.modules.admin.services import AdminBannerService

    response_body, status_code = success_response(
        data=AdminBannerService.public_active()
    )

    response = make_response(
        response_body,
        status_code,
    )

    response.headers["Cache-Control"] = "no-store, max-age=0"

    return response
