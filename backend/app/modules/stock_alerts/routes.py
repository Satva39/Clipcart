from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.modules.accounts.decorators import customer_required
from app.utils.response import error_response, success_response
from .services import StockAlertService

stock_alerts_bp = Blueprint("stock_alerts", __name__, url_prefix="/api/stock-alerts")


def _ids(data):
    try:
        product_id = int(data.get("product_id"))
        variant_raw = data.get("variant_id")
        variant_id = None if variant_raw in (None, "", "null") else int(variant_raw)
    except (TypeError, ValueError):
        raise ValueError("Invalid product or variant.")
    return product_id, variant_id


@stock_alerts_bp.get("/status")
@customer_required
def status():
    account_id = int(get_jwt_identity())
    try:
        product_id, variant_id = _ids(request.args)
        return success_response(
            data=StockAlertService.status(account_id, product_id, variant_id)
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)


@stock_alerts_bp.post("/")
@customer_required
def subscribe():
    account_id = int(get_jwt_identity())
    try:
        product_id, variant_id = _ids(request.get_json(silent=True) or {})
        result = StockAlertService.subscribe(account_id, product_id, variant_id)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(message="Stock alert enabled.", data=result)


@stock_alerts_bp.delete("/")
@customer_required
def unsubscribe():
    account_id = int(get_jwt_identity())
    try:
        product_id, variant_id = _ids(request.args)
        if request.is_json:
            product_id, variant_id = _ids(request.get_json(silent=True) or {})
        result = StockAlertService.unsubscribe(account_id, product_id, variant_id)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(message="Stock alert disabled.", data=result)
