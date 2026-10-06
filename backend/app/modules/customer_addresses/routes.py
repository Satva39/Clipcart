from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.modules.accounts.decorators import customer_required
from app.utils.response import error_response, success_response

from .repository import CustomerAddressRepository
from .schemas import CustomerAddressSchema
from .services import CustomerAddressService

customer_addresses_bp = Blueprint(
    "customer_addresses",
    __name__,
    url_prefix="/api/customer-addresses",
)


def serialize_address(address):
    return {
        "id": address.id,
        "full_name": address.full_name,
        "phone": address.phone,
        "address_line_1": address.address_line_1,
        "address_line_2": address.address_line_2,
        "landmark": address.landmark,
        "city": address.city,
        "state": address.state,
        "postal_code": address.postal_code,
        "country": address.country,
        "latitude": float(address.latitude) if address.latitude is not None else None,
        "longitude": float(address.longitude) if address.longitude is not None else None,
        "is_default": address.is_default,
    }


@customer_addresses_bp.post("/")
@customer_required
def create():
    account_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    errors = CustomerAddressSchema().validate(data)
    if errors:
        return error_response(message=errors, status_code=400)

    try:
        address = CustomerAddressService.create(account_id, data)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(
        message="Address created.",
        data=serialize_address(address),
        status_code=201,
    )


@customer_addresses_bp.get("/")
@customer_required
def list_addresses():
    account_id = int(get_jwt_identity())
    addresses = CustomerAddressService.get_all(account_id)
    return success_response(data=[serialize_address(address) for address in addresses])


@customer_addresses_bp.put("/<int:address_id>")
@customer_required
def update_address(address_id):
    account_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    errors = CustomerAddressSchema(partial=True).validate(data)
    if errors:
        return error_response(message=errors, status_code=400)

    try:
        address = CustomerAddressService.update(account_id, address_id, data)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=404)

    return success_response(
        message="Address updated.",
        data=serialize_address(address),
    )


@customer_addresses_bp.put("/<int:address_id>/default")
@customer_required
def set_default(address_id):
    account_id = int(get_jwt_identity())
    try:
        address = CustomerAddressService.set_default(account_id, address_id)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=404)
    return success_response(
        message="Default address updated.",
        data=serialize_address(address),
    )


@customer_addresses_bp.delete("/<int:address_id>")
@customer_required
def delete_address(address_id):
    account_id = int(get_jwt_identity())
    try:
        CustomerAddressService.delete(account_id, address_id)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=404)

    return success_response(message="Address deleted.")
