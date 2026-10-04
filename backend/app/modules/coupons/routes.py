from flask import Blueprint, request

from flask_jwt_extended import get_jwt_identity
from app.core.decorators import active_supplier_required

from app.utils.response import (
    success_response,
    error_response,
)

from .schemas import CouponCreateSchema
from .services import CouponService

coupons_bp = Blueprint(
    "coupons",
    __name__,
    url_prefix="/api/coupons",
)


@coupons_bp.post("/")
@active_supplier_required
def create_coupon():

    seller_id = int(get_jwt_identity())

    data = request.get_json()

    errors = CouponCreateSchema().validate(data)

    if errors:
        return error_response(
            message=errors,
            status_code=400,
        )

    try:

        coupon = CouponService.create(
            data,
            seller_id,
        )

    except ValueError as e:

        return error_response(
            message=str(e),
            status_code=400,
        )

    return success_response(
        message="Coupon created.",
        data={
            "id": coupon.id,
            "code": coupon.code,
        },
        status_code=201,
    )


@coupons_bp.post("/validate")
def validate_coupon():

    data = request.get_json()

    try:

        coupon = CouponService.validate(
            data["code"],
            data["order_total"],
        )

    except ValueError as e:

        return error_response(
            message=str(e),
            status_code=400,
        )

    return success_response(
        data={
            "code": coupon.code,
            "discount_type": coupon.discount_type.value,
            "discount_value": float(coupon.discount_value),
        }
    )
