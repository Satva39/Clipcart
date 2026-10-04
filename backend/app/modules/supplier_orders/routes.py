from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db

from app.modules.accounts.decorators import active_logistics_required
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.models import Account
from app.modules.accounts.services import login_account
from app.modules.notifications.models import Notification
from app.shared.utils.api_response import error, success

from .schemas import (
    AssignAgentSchema,
    DeliveryAttemptSchema,
    DeliveryNotesSchema,
    FailedDeliverySchema,
)
from .services import DeliveryAssignmentService

supplier_orders_bp = Blueprint(
    "supplier_orders",
    __name__,
    url_prefix="/api/logistics",
)


def _manager():
    try:
        account_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    account = Account.query.get(account_id)
    if (
        not account
        or account.role != UserRole.LOGISTICS_MANAGER
        or account.status != UserStatus.ACTIVE
    ):
        return None
    return account


@supplier_orders_bp.post("/auth/login")
def logistics_login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        return error("Email and password are required.", 400)

    result = login_account(email, password)
    if not result:
        return error("Invalid email or password.", 401)

    account = result["account"]
    if (
        account.role != UserRole.LOGISTICS_MANAGER
        or account.status != UserStatus.ACTIVE
    ):
        return error("This account is not authorized for the logistics portal.", 403)

    return success(
        "Logistics login successful.",
        {
            "user": {
                "id": account.id,
                "full_name": account.full_name,
                "email": account.email,
                "role": account.role.value,
                "status": account.status.value,
            },
            **result["tokens"],
        },
    )


@supplier_orders_bp.get("/auth/me")
@active_logistics_required
def logistics_me():
    account = _manager()
    if not account:
        return error("Logistics account not found.", 403)
    return success(
        "Logistics profile loaded.",
        {
            "id": account.id,
            "full_name": account.full_name,
            "email": account.email,
            "role": account.role.value,
            "status": account.status.value,
        },
    )


@supplier_orders_bp.get("/dashboard")
@active_logistics_required
def dashboard():
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    return success(data=DeliveryAssignmentService.get_dashboard(account.id))


@supplier_orders_bp.get("/orders")
@active_logistics_required
def get_queue():
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    try:
        data = DeliveryAssignmentService.get_queue(
            search=request.args.get("search"),
            stage=request.args.get("stage"),
            status=request.args.get("status"),
            date=request.args.get("date"),
            agent=request.args.get("agent"),
            pending_action=request.args.get("pending_action"),
        )
        return success(data=data)
    except ValueError as exc:
        return error(str(exc), 400)


@supplier_orders_bp.get("/orders/<int:order_id>")
@active_logistics_required
def get_order(order_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    data = DeliveryAssignmentService.get_for_order(order_id)
    if data is None:
        return error("Order not found or not available to logistics.", 404)
    return success(data=data)


@supplier_orders_bp.put("/orders/<int:order_id>/assign")
@active_logistics_required
def assign_agent(order_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    payload = request.get_json(silent=True)
    if payload is None:
        return error("Request body must be valid JSON.", 415)
    errors = AssignAgentSchema().validate(payload)
    if errors:
        return error(errors, 400)
    try:
        data = DeliveryAssignmentService.assign_agent(
            order_id,
            payload["agent_name"],
            payload["agent_phone"],
            account.id,
        )
        if data is None:
            return error("Order not found or not available to logistics.", 404)
        return success("Delivery agent assigned.", data)
    except ValueError as exc:
        return error(str(exc), 400)


@supplier_orders_bp.put("/orders/<int:order_id>/pickup")
@active_logistics_required
def mark_picked_up(order_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    try:
        data = DeliveryAssignmentService.mark_picked_up(order_id)
        if data is None:
            return error("Order not found or not available to logistics.", 404)
        return success("Marked as picked up.", data)
    except ValueError as exc:
        return error(str(exc), 400)


@supplier_orders_bp.put("/orders/<int:order_id>/out-for-delivery")
@active_logistics_required
def mark_out_for_delivery(order_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    try:
        data = DeliveryAssignmentService.mark_out_for_delivery(order_id)
        if data is None:
            return error("Order not found or not available to logistics.", 404)
        return success("Marked out for delivery.", data)
    except ValueError as exc:
        return error(str(exc), 400)


@supplier_orders_bp.put("/orders/<int:order_id>/attempt")
@active_logistics_required
def record_attempt(order_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    payload = request.get_json(silent=True)
    if payload is None:
        return error("Request body must be valid JSON.", 415)
    errors = DeliveryAttemptSchema().validate(payload)
    if errors:
        return error(errors, 400)
    try:
        data = DeliveryAssignmentService.record_attempt(
            order_id,
            payload["reason"],
            payload.get("notes", ""),
        )
        if data is None:
            return error("Order not found or not available to logistics.", 404)
        return success("Delivery attempt recorded.", data)
    except ValueError as exc:
        return error(str(exc), 400)


@supplier_orders_bp.put("/orders/<int:order_id>/deliver")
@active_logistics_required
def mark_delivered(order_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    payload = (
        request.form.to_dict()
        if request.files
        else (request.get_json(silent=True) or {})
    )
    errors = DeliveryNotesSchema().validate(payload)
    if errors:
        return error(errors, 400)
    completion_photo = request.files.get("completion_photo")
    try:
        data = DeliveryAssignmentService.mark_delivered(
            order_id,
            payload.get("notes", ""),
            payload.get("customer_delivery_notes", ""),
            payload.get("proof_of_delivery_reference", ""),
            completion_photo=completion_photo,
        )
        if data is None:
            return error("Order not found or not available to logistics.", 404)
        return success("Marked as delivered.", data)
    except ValueError as exc:
        return error(str(exc), 400)


@supplier_orders_bp.put("/orders/<int:order_id>/fail")
@active_logistics_required
def mark_failed(order_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    payload = request.get_json(silent=True)
    if payload is None:
        return error("Request body must be valid JSON.", 415)
    errors = FailedDeliverySchema().validate(payload)
    if errors:
        return error(errors, 400)
    try:
        data = DeliveryAssignmentService.mark_failed(
            order_id,
            payload["reason"],
            payload["next_action"],
            payload.get("notes", ""),
        )
        if data is None:
            return error("Order not found or not available to logistics.", 404)
        return success("Delivery failure recorded.", data)
    except ValueError as exc:
        return error(str(exc), 400)


@supplier_orders_bp.put("/orders/<int:order_id>/retry")
@active_logistics_required
def retry_failed(order_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    payload = request.get_json(silent=True) or {}
    errors = DeliveryNotesSchema().validate(payload)
    if errors:
        return error(errors, 400)
    try:
        data = DeliveryAssignmentService.retry_failed(
            order_id, payload.get("notes", "")
        )
        if data is None:
            return error("Order not found or not available to logistics.", 404)
        return success("Delivery retry started.", data)
    except ValueError as exc:
        return error(str(exc), 400)


@supplier_orders_bp.get("/notifications")
@active_logistics_required
def notifications():
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    unread_only = request.args.get("unread", "").lower() in {"1", "true", "yes"}
    return success(
        data=DeliveryAssignmentService.get_notifications(
            account.id, unread_only=unread_only
        )
    )


@supplier_orders_bp.get("/notifications/unread-count")
@active_logistics_required
def unread_notifications():
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    count = DeliveryAssignmentService.get_notifications(
        account.id, unread_only=True, limit=100
    )
    return success(data={"count": len(count)})


@supplier_orders_bp.put("/notifications/<int:notification_id>/read")
@active_logistics_required
def read_notification(notification_id):
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    notification = Notification.query.filter_by(
        id=notification_id, account_id=account.id
    ).first()
    if not notification:
        return error("Notification not found.", 404)
    notification.is_read = True
    db.session.commit()
    return success("Notification marked as read.")


@supplier_orders_bp.put("/notifications/read-all")
@active_logistics_required
def read_all_notifications():
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    Notification.query.filter_by(account_id=account.id, is_read=False).update(
        {"is_read": True}, synchronize_session=False
    )
    db.session.commit()
    return success("All notifications marked as read.")


@supplier_orders_bp.get("/history")
@active_logistics_required
def completed_history():
    account = _manager()
    if not account:
        return error("Logistics access required.", 403)
    try:
        limit = int(request.args.get("limit", 100))
    except (TypeError, ValueError):
        limit = 100
    return success(data=DeliveryAssignmentService.get_completed_history(limit=limit))
