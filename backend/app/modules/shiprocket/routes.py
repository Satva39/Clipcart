from flask import Blueprint, current_app, request, send_file
import io
import requests
from flask_jwt_extended import get_jwt_identity

from app.modules.accounts.decorators import active_logistics_required
from app.core.decorators import active_supplier_required
from app.modules.admin.authorization import admin_authorized
from app.modules.orders.models import Order
from app.shared.utils.api_response import error, success

from .service import ShiprocketError, ShiprocketService

shiprocket_bp = Blueprint("shiprocket", __name__, url_prefix="/api")


@shiprocket_bp.post("/webhooks/delivery-status")
def delivery_status_webhook():
    configured_secret = str(
        current_app.config.get("SHIPROCKET_WEBHOOK_SECRET") or ""
    ).strip()
    if not configured_secret:
        return error("Shiprocket webhook is not configured.", 503)
    provided = str(request.headers.get("x-api-key") or "").strip()
    if not provided or provided != configured_secret:
        return error("Invalid webhook authentication.", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error("Webhook body must be valid JSON.", 400)
    try:
        ShiprocketService.apply_webhook(payload)
    except ShiprocketError as exc:
        if exc.code == "WEBHOOK_SHIPMENT_NOT_FOUND":
            return success("Webhook ignored because no Clipcart shipment matches it.")
        return error(str(exc), 400)
    return success("Webhook processed.")


@shiprocket_bp.post("/integrations/shipments/<int:order_id>/retry")
@active_logistics_required
def retry_shipments(order_id):
    try:
        rows = ShiprocketService.retry_order(order_id)
    except ShiprocketError as exc:
        return error(str(exc), 400)
    return success(
        "Shiprocket shipment provisioning retried.",
        [
            ShiprocketService._serialize_shipment(row, include_supplier=True)
            for row in rows
        ],
    )


@shiprocket_bp.post("/admin/shipments/<int:order_id>/retry")
@admin_authorized
def admin_retry_shipments(order_id):
    try:
        rows = ShiprocketService.retry_order(order_id)
    except ShiprocketError as exc:
        return error(str(exc), 400)
    return success(
        "Shiprocket shipment provisioning retried.",
        [
            ShiprocketService._serialize_shipment(row, include_supplier=True)
            for row in rows
        ],
    )


@shiprocket_bp.get("/integrations/shipments/<int:shipment_id>/label")
@active_supplier_required
def supplier_label(shipment_id):
    from .models import Shipment
    shipment = Shipment.query.get(shipment_id)
    if not shipment:
        return error("Shipment not found.", 404)
    account_id = int(get_jwt_identity())
    if shipment.supplier_id != account_id:
        return error("Shipment not found.", 404)
    if not shipment.label_url:
        return error("Shipping label is not ready yet.", 404)
    try:
        response = requests.get(shipment.label_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        return error("Shipping label could not be downloaded right now.", 502)
    return send_file(
        io.BytesIO(response.content),
        mimetype=response.headers.get("Content-Type", "application/pdf"),
        as_attachment=False,
        download_name=f"clipcart-order-{shipment.order_id}-label.pdf",
    )

@shiprocket_bp.post("/integrations/shipments/<int:shipment_id>/label")
@active_supplier_required
def regenerate_label(shipment_id):
    from .models import Shipment
    shipment = Shipment.query.get(shipment_id)
    if not shipment:
        return error("Shipment not found.", 404)
    account_id = int(get_jwt_identity())
    if shipment.supplier_id != account_id:
        return error("Shipment not found.", 404)
    try:
        ShiprocketService._generate_label(shipment)
    except ShiprocketError as exc:
        return error(str(exc), 400)
    return success("Shipping label is ready.", ShiprocketService._serialize_shipment(shipment))

@shiprocket_bp.get("/admin/shiprocket/diagnostics")
@admin_authorized
def shiprocket_diagnostics():
    order_id = request.args.get("order_id", type=int)
    return success(data=ShiprocketService.diagnostics(order_id=order_id))


@shiprocket_bp.get("/admin/shipments/<int:order_id>")
@admin_authorized
def admin_shipments(order_id):
    order = Order.query.get(order_id)
    if not order:
        return error("Order not found.", 404)
    return success(data=ShiprocketService.get_logistics_shipments(order))


@shiprocket_bp.get("/integrations/shipments/<int:order_id>")
@active_logistics_required
def logistics_shipments(order_id):
    order = Order.query.get(order_id)
    if not order:
        return error("Order not found.", 404)
    return success(data=ShiprocketService.get_logistics_shipments(order))
