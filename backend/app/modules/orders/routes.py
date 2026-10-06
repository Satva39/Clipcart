from flask import Blueprint, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.modules.accounts.decorators import customer_required
from app.core.decorators import active_supplier_required
from app.services.invoice_service import InvoiceService
from app.modules.shiprocket.service import ShiprocketError
from app.utils.response import error_response, success_response
from .models import Order
from .services import OrderService

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.get("/health")
def health():
    return success_response(message="Orders module working.")


@orders_bp.get("/")
@customer_required
def my_orders():
    return success_response(data=OrderService.get_orders(int(get_jwt_identity())))


@orders_bp.get("/active")
@customer_required
def active_orders():
    return success_response(
        data=OrderService.get_active_orders(int(get_jwt_identity()))
    )


@orders_bp.get("/reviewable")
@customer_required
def reviewable_orders():
    return success_response(
        data=OrderService.get_reviewable_items(
            int(get_jwt_identity()), request.args.get("product_id", type=int)
        )
    )


@orders_bp.get("/<int:order_id>")
@customer_required
def order_detail(order_id):
    order = OrderService.get_order(int(get_jwt_identity()), order_id)
    if not order:
        return error_response(message="Order not found.", status_code=404)
    return success_response(data=order)


@orders_bp.get("/<int:order_id>/tracking")
@customer_required
def tracking(order_id):
    order = OrderService.get_tracking(
        int(get_jwt_identity()),
        order_id,
        force_refresh=request.args.get("refresh", "0") == "1",
    )
    if not order:
        return error_response(message="Order not found.", status_code=404)
    return success_response(data=order)


@orders_bp.get("/<int:order_id>/invoice")
@customer_required
def invoice_download(order_id):
    account_id = int(get_jwt_identity())
    order = OrderService.get_order(account_id, order_id)
    if not order:
        return error_response(message="Order not found.", status_code=404)
    model = Order.query.filter_by(id=order_id, account_id=account_id).first()
    if not model:
        return error_response(message="Order not found.", status_code=404)
    try:
        path = InvoiceService.generate(model)
    except Exception:
        return error_response(
            message="Invoice could not be generated.", status_code=500
        )
    return send_file(
        path,
        as_attachment=True,
        download_name=f"{model.invoice.invoice_number}.pdf",
        mimetype="application/pdf",
    )


@orders_bp.put("/<int:order_id>/cancel")
@customer_required
def cancel_order(order_id):
    try:
        result = OrderService.cancel_order(
            int(get_jwt_identity()),
            order_id,
            (request.get_json(silent=True) or {}).get("reason"),
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(message="Order cancellation recorded.", data=result)


@orders_bp.get("/supplier")
@jwt_required()
@active_supplier_required
def supplier_orders():
    return success_response(
        data=OrderService.get_supplier_orders(
            int(get_jwt_identity()),
            request.args.get("status"),
            request.args.get("search"),
            request.args.get("page", 1, type=int),
            request.args.get("per_page", 25, type=int),
        )
    )


@orders_bp.post("/supplier/import")
@jwt_required()
@active_supplier_required
def import_supplier_orders():
    upload = request.files.get("file")
    if upload is None:
        return error_response("CSV file is required.", 400)
    try:
        content = upload.read(2 * 1024 * 1024 + 1)
        if len(content) > 2 * 1024 * 1024:
            raise ValueError("CSV must be 2 MB or smaller.")
        result = OrderService.import_supplier_status_csv(
            int(get_jwt_identity()), content, upload.filename
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    except ShiprocketError as exc:
        return error_response(
            message=(
                "Orders were updated, but Shiprocket shipment setup needs attention: "
                f"{str(exc)}"
            ),
            status_code=502,
        )
    return success_response("CSV imported successfully.", data=result)


@orders_bp.get("/supplier/<int:order_id>")
@jwt_required()
@active_supplier_required
def supplier_order_detail(order_id):
    order = OrderService.get_supplier_order(int(get_jwt_identity()), order_id)
    if not order:
        return error_response(message="Order not found.", status_code=404)
    return success_response(data=order)


@orders_bp.put("/supplier/<int:order_id>/status")
@jwt_required()
@active_supplier_required
def update_order_status(order_id):
    try:
        order = OrderService.update_supplier_status(
            int(get_jwt_identity()),
            order_id,
            (request.get_json(silent=True) or {}).get("status"),
        )
        return success_response(
            message="Order updated successfully.",
            data={"id": order.id, "status": order.status.value},
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    except ShiprocketError as exc:
        return error_response(
            message=(
                "Order moved to processing, but Shiprocket shipment setup needs attention: "
                f"{str(exc)}"
            ),
            status_code=502,
        )


@orders_bp.get("/supplier/earnings")
@jwt_required()
@active_supplier_required
def supplier_earnings():
    return success_response(
        data=OrderService.get_supplier_earnings(int(get_jwt_identity()))
    )
