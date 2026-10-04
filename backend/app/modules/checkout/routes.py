from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.modules.accounts.decorators import customer_required
from app.utils.response import success_response, error_response
from .services import CheckoutService

checkout_bp = Blueprint("checkout", __name__, url_prefix="/api/checkout")


@checkout_bp.post("/session")
@customer_required
def create_session():
    try:
        data = CheckoutService.get_session(int(get_jwt_identity()))
        return success_response(data=data)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)


@checkout_bp.get("/session")
@customer_required
def get_session():
    try:
        data = CheckoutService.get_session(int(get_jwt_identity()))
        return success_response(data=data)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)


@checkout_bp.post("/validate")
@customer_required
def validate():
    try:
        return success_response(
            data=CheckoutService.validate_checkout(int(get_jwt_identity()))
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)


@checkout_bp.put("/address")
@customer_required
def select_address():
    try:
        data = request.get_json(silent=True) or {}
        result = CheckoutService.set_address(
            int(get_jwt_identity()), data.get("address_id")
        )
        return success_response(message="Delivery address selected.", data=result)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)


@checkout_bp.put("/coupon")
@customer_required
def apply_coupon():
    try:
        data = request.get_json(silent=True) or {}
        result = CheckoutService.apply_coupon(int(get_jwt_identity()), data.get("code"))
        return success_response(message="Checkout updated.", data=result)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)


@checkout_bp.post("/razorpay-order")
@customer_required
def razorpay_order():
    try:
        order = CheckoutService.create_razorpay_order(int(get_jwt_identity()))
        return success_response(data=order)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    except RuntimeError as exc:
        return error_response(message=str(exc), status_code=502)


@checkout_bp.post("/payment-failed")
@customer_required
def payment_failed():
    try:
        result = CheckoutService.payment_failed(
            int(get_jwt_identity()),
            request.get_json(silent=True) or {},
        )
        return success_response(message=result["message"], data=result)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)


@checkout_bp.post("/verify-payment")
@customer_required
def verify_payment():
    try:
        result = CheckoutService.verify_payment(
            int(get_jwt_identity()),
            request.get_json(silent=True) or {},
        )
        return success_response(
            message="Payment verified and order confirmed.", data=result
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    except Exception:
        return error_response(message="Payment verification failed.", status_code=400)


@checkout_bp.post("/create-order")
@customer_required
def create_order():
    try:
        order = CheckoutService.create_order(int(get_jwt_identity()))
        return success_response(
            message="Order confirmed.",
            data={"order_id": order.id, "status": order.status.value},
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
