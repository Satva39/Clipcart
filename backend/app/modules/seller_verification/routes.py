from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.modules.accounts.decorators import supplier_required, active_supplier_required
from app.utils.response import success_response, error_response
from .services import SellerVerificationService
from .schemas import SellerVerificationSchema

seller_verification_bp = Blueprint(
    "seller_verification",
    __name__,
    url_prefix="/api/seller-verification",
)


@seller_verification_bp.get("/status")
@jwt_required()
@supplier_required
def status():
    account_id = int(get_jwt_identity())
    return success_response(
        data={"verified": SellerVerificationService.is_verified(account_id)}
    )


@seller_verification_bp.put("/business")
@jwt_required()
@active_supplier_required
def update_business():
    data = request.get_json(silent=True) or {}
    errors = SellerVerificationSchema().validate(data)
    if errors:
        return error_response(message=errors, status_code=400)

    account_id = int(get_jwt_identity())
    try:
        verification = SellerVerificationService.update_business_details(
            account_id=account_id,
            business_name=data["business_name"],
            gst_number=data.get("gst_number"),
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)

    return success_response(
        message="Business details updated.",
        data={
            "business_name": verification.business_name,
            "gst_number": verification.gst_number,
            "status": verification.status,
        },
    )
