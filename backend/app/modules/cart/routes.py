from flask import Blueprint, request
from app.modules.accounts.decorators import customer_required

from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
)

from app.utils.response import success_response
from app.utils.response import error_response
from .services import CartService

cart_bp = Blueprint(
    "cart",
    __name__,
    url_prefix="/api/cart",
)


@cart_bp.get("/")
@customer_required
def get_cart():

    account_id = int(get_jwt_identity())

    cart = CartService.get(account_id)

    return success_response(data=cart)


@cart_bp.post("/", strict_slashes=False)
@customer_required
def add_to_cart():

    account_id = int(get_jwt_identity())
    data = request.get_json()

    try:

        CartService.add(
            account_id=account_id,
            product_id=data["product_id"],
            variant_id=data.get("variant_id"),
            quantity=data.get("quantity", 1),
        )

    except ValueError as e:

        return error_response(
            message=str(e),
            status_code=400,
        )

    return success_response(message="Added to cart.")


@cart_bp.put("/")
@customer_required
def update_cart():

    account_id = int(get_jwt_identity())
    data = request.get_json() or {}

    try:
        raw_product_id = str(data["product_id"])

        # Supports values like "1-default"
        if "-" in raw_product_id:
            raw_product_id = raw_product_id.split("-")[0]

        product_id = int(raw_product_id)

        quantity = int(data["quantity"])

        raw_variant_id = data.get("variant_id")

        if (
            raw_variant_id is None
            or raw_variant_id == ""
            or raw_variant_id == "default"
        ):
            variant_id = None
        else:
            variant_id = int(raw_variant_id)

        item = CartService.update_quantity(
            account_id=account_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
        )

        if not item:
            return error_response(
                message="Cart item not found.",
                status_code=404,
            )

        return success_response(message="Cart updated.")

    except (KeyError, TypeError, ValueError):
        return error_response(
            message="Invalid cart data.",
            status_code=400,
        )


@cart_bp.delete("/", strict_slashes=False)
@customer_required
def remove_from_cart():

    account_id = int(get_jwt_identity())
    data = request.get_json()

    CartService.remove(
        account_id=account_id,
        product_id=data["product_id"],
        variant_id=data.get("variant_id"),
    )

    return success_response(message="Removed from cart.")
