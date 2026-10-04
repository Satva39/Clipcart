from flask import Blueprint
from app.modules.accounts.decorators import customer_or_supplier_required

from flask import request
from flask_jwt_extended import get_jwt_identity

from app.utils.response import success_response
from app.utils.response import error_response
from app.extensions import db

from .services import NotificationService
from .enums import NotificationType

notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications",
)


@notifications_bp.post("/")
@customer_or_supplier_required
def create():
    account_id = int(get_jwt_identity())

    NotificationService.create(
        account_id,
        "Welcome",
        "Notification created successfully.",
        NotificationType.SYSTEM,
    )
    db.session.commit()

    return success_response(message="Notification created.")


@notifications_bp.get("/")
@customer_or_supplier_required
def all_notifications():
    account_id = int(get_jwt_identity())
    return success_response(data=NotificationService.list(account_id))


@notifications_bp.put("/<int:notification_id>/read")
@customer_or_supplier_required
def read(notification_id):
    account_id = int(get_jwt_identity())

    try:
        NotificationService.read(account_id, notification_id)
    except ValueError as e:
        return error_response(message=str(e), status_code=400)

    return success_response(message="Notification marked as read.")


@notifications_bp.put("/read-all")
@customer_or_supplier_required
def read_all():
    account_id = int(get_jwt_identity())
    NotificationService.read_all(account_id)
    return success_response(message="All notifications marked as read.")


@notifications_bp.get("/unread-count")
@customer_or_supplier_required
def unread():
    account_id = int(get_jwt_identity())
    return success_response(data={"count": NotificationService.unread(account_id)})


@notifications_bp.delete("/<int:notification_id>")
@customer_or_supplier_required
def delete(notification_id):
    account_id = int(get_jwt_identity())

    try:
        NotificationService.delete(account_id, notification_id)
    except ValueError as e:
        return error_response(message=str(e), status_code=400)

    return success_response(message="Notification deleted.")
