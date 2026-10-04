from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.utils.response import success_response, error_response
from .schemas import ProductWizardSchema
from .services import ProductWizardService

wizard_bp = Blueprint(
    "product_wizard",
    __name__,
    url_prefix="/api/product-wizard",
)


@wizard_bp.post("/")
@jwt_required()
def create_product():

    data = request.get_json()

    errors = ProductWizardSchema().validate(data)

    if errors:
        return error_response(
            message=errors,
            status_code=400,
        )

    current_user = get_jwt_identity()

    product = ProductWizardService.create(
        data,
        current_user["id"],
    )

    return success_response(
        message="Product published successfully.",
        data={
            "product_id": product.id,
        },
        status_code=201,
    )