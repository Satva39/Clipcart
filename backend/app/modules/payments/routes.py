from flask import Blueprint
from app.shared.utils.api_response import error

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


@payments_bp.post("/seller-registration/order")
def create_seller_registration_order_legacy():
    return error(
        "Use /api/supplier-registration/payment/order for the protected supplier onboarding payment flow.",
        410,
    )
