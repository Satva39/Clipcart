from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.modules.accounts.decorators import active_logistics_required, customer_required
from app.utils.response import error_response, success_response

from .services import ReturnService

returns_bp = Blueprint("returns", __name__, url_prefix="/api/returns")


def _logistics_account_id():
    try:
        return int(get_jwt_identity())
    except (TypeError, ValueError):
        return None


@returns_bp.get("/")
@customer_required
def list_returns():
    account_id = int(get_jwt_identity())
    return success_response(data=ReturnService.list_for_customer(account_id))


@returns_bp.post("/")
@customer_required
def create_return():
    account_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    try:
        result = ReturnService.create(
            account_id=account_id,
            order_id=data.get("order_id"),
            order_item_id=data.get("order_item_id"),
            reason=data.get("reason"),
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)

    return success_response(
        message="Return request submitted.",
        data=result,
        status_code=201,
    )


@returns_bp.put("/<int:return_id>/cancel")
@customer_required
def cancel_return(return_id):
    account_id = int(get_jwt_identity())
    try:
        result = ReturnService.cancel(account_id, return_id)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(message="Return request cancelled.", data=result)


@returns_bp.get("/logistics")
@active_logistics_required
def logistics_returns():
    if _logistics_account_id() is None:
        return error_response(message="Logistics access required.", status_code=403)
    return success_response(data=ReturnService.list_for_logistics())


@returns_bp.get("/logistics/<int:return_id>")
@active_logistics_required
def logistics_return_detail(return_id):
    if _logistics_account_id() is None:
        return error_response(message="Logistics access required.", status_code=403)
    data = ReturnService.get_for_logistics(return_id)
    if data is None:
        return error_response(message="Return request not found.", status_code=404)
    return success_response(data=data)


@returns_bp.put("/logistics/<int:return_id>/assign")
@active_logistics_required
def logistics_assign_pickup(return_id):
    if _logistics_account_id() is None:
        return error_response(message="Logistics access required.", status_code=403)
    data = request.get_json(silent=True) or {}
    try:
        result = ReturnService.assign_pickup(
            return_id=return_id,
            agent_name=data.get("agent_name"),
            agent_phone=data.get("agent_phone"),
            notes=data.get("notes", ""),
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    if result is None:
        return error_response(message="Return request not found.", status_code=404)
    return success_response(message="Return pickup agent assigned.", data=result)


@returns_bp.put("/logistics/<int:return_id>/pickup")
@active_logistics_required
def logistics_pickup(return_id):
    if _logistics_account_id() is None:
        return error_response(message="Logistics access required.", status_code=403)
    data = request.get_json(silent=True) or {}
    try:
        result = ReturnService.mark_picked_up(
            return_id=return_id,
            notes=data.get("notes", ""),
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    if result is None:
        return error_response(message="Return request not found.", status_code=404)
    return success_response(message="Return picked up from customer.", data=result)


@returns_bp.put("/logistics/<int:return_id>/deliver-to-supplier")
@active_logistics_required
def logistics_deliver_to_supplier(return_id):
    if _logistics_account_id() is None:
        return error_response(message="Logistics access required.", status_code=403)
    data = (
        request.form.to_dict()
        if request.files
        else (request.get_json(silent=True) or {})
    )
    completion_photo = request.files.get("completion_photo")
    try:
        result = ReturnService.deliver_to_supplier(
            return_id=return_id,
            notes=data.get("notes", ""),
            completion_photo=completion_photo,
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    if result is None:
        return error_response(message="Return request not found.", status_code=404)
    return success_response(message="Return delivered to supplier.", data=result)
