from flask import Blueprint
from app.modules.accounts.decorators import customer_required

from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
)

from app.utils.response import success_response
from .services import WishlistService

wishlist_bp = Blueprint(
    "wishlist",
    __name__,
    url_prefix="/api/wishlist",
)


@wishlist_bp.get("/")
@customer_required
def get_wishlist():

    account_id = int(get_jwt_identity())
    items = WishlistService.get(account_id)

    return success_response(
        data=[
            {
                "id": item.product.id,
                "name": item.product.name,
                "slug": item.product.slug,
                "price": float(item.product.price),
                "compare_price": (
                    float(item.product.compare_price)
                    if item.product.compare_price is not None
                    else None
                ),
                "stock": item.product.stock,
                "discount_percent": (
                    round(
                        (
                            (
                                float(item.product.compare_price)
                                - float(item.product.price)
                            )
                            / float(item.product.compare_price)
                        )
                        * 100
                    )
                    if item.product.compare_price
                    and item.product.compare_price > item.product.price
                    else 0
                ),
                "category": (
                    item.product.category.name if item.product.category else None
                ),
                "image": (
                    item.product.images[0].image_url if item.product.images else None
                ),
            }
            for item in items
        ]
    )


@wishlist_bp.post("/<int:product_id>")
@customer_required
def add(product_id):

    account_id = int(get_jwt_identity())

    WishlistService.add(
        account_id,
        product_id,
    )

    return success_response(message="Added to wishlist.")


@wishlist_bp.delete("/<int:product_id>")
@customer_required
def remove(product_id):

    account_id = int(get_jwt_identity())

    WishlistService.remove(
        account_id,
        product_id,
    )

    return success_response(message="Removed from wishlist.")
