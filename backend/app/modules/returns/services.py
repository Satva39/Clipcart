from datetime import datetime

from flask import current_app
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.models import Account
from app.modules.admin.services import AdminNotificationService
from app.modules.notifications.enums import NotificationType
from app.modules.notifications.services import NotificationService
from app.modules.order_events.services import OrderEventService
from app.modules.order_items.models import OrderItem
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.modules.seller_verification.models import SellerVerification
from app.modules.uploads.services import UploadService

from .models import ReturnRequest

ACTIVE_RETURN_STATUSES = {
    "REQUESTED",
    "APPROVED",
    "PICKUP_ASSIGNED",
    "PICKED_UP",
    "IN_TRANSIT_TO_SUPPLIER",
}
TERMINAL_RETURN_STATUSES = {"RECEIVED", "CANCELLED", "REJECTED"}
LOGISTICS_ASSIGNABLE_STATUSES = {"REQUESTED", "APPROVED"}


def _safe_datetime(value):
    return value.isoformat() if value else None


def _supplier_for_item(order_item):
    return order_item.product.seller if order_item and order_item.product else None


def _supplier_business_name(supplier):
    if not supplier:
        return None
    verification = SellerVerification.query.filter_by(account_id=supplier.id).first()
    return (verification.business_name if verification else None) or supplier.full_name


def _order_item_image_url(order_item):
    if not order_item:
        return None

    variant = order_item.variant
    if variant and getattr(variant, "images", None):
        images = list(variant.images)
        image = next((row for row in images if row.is_thumbnail), None)
        image = image or (images[0] if images else None)
        if image:
            return image.image_url

    product = order_item.product
    if product and getattr(product, "images", None):
        images = [row for row in product.images if row.variant_id is None]
        image = next((row for row in images if row.is_thumbnail), None)
        image = image or (images[0] if images else None)
        if image:
            return image.image_url

    return None


def _serialize(item, include_logistics=False):
    order = item.order
    order_item = item.order_item
    supplier = _supplier_for_item(order_item)
    data = {
        "id": item.id,
        "order_id": item.order_id,
        "order_item_id": item.order_item_id,
        "reason": item.reason,
        "status": item.status,
        "resolution_note": item.resolution_note,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "resolved_at": item.resolved_at,
    }

    if include_logistics:
        data.update(
            {
                "customer": {
                    "name": order.delivery_full_name if order else None,
                    "phone": order.delivery_phone if order else None,
                    "address": {
                        "address_line_1": (
                            order.delivery_address_line_1 if order else None
                        ),
                        "address_line_2": (
                            order.delivery_address_line_2 if order else None
                        ),
                        "landmark": order.delivery_landmark if order else None,
                        "city": order.delivery_city if order else None,
                        "state": order.delivery_state if order else None,
                        "postal_code": order.delivery_postal_code if order else None,
                        "country": order.delivery_country if order else None,
                    },
                },
                "supplier": {
                    "id": supplier.id if supplier else None,
                    "name": supplier.full_name if supplier else None,
                    "business_name": _supplier_business_name(supplier),
                    "phone": supplier.phone if supplier else None,
                    "return_address": None,
                },
                "item": {
                    "id": order_item.id if order_item else None,
                    "product_id": order_item.product_id if order_item else None,
                    "product_name": (
                        order_item.product_name_snapshot if order_item else None
                    ),
                    "variant": (
                        order_item.variant_value_snapshot
                        if order_item and order_item.variant_value_snapshot
                        else (
                            order_item.variant.value
                            if order_item and order_item.variant
                            else None
                        )
                    ),
                    "quantity": int(order_item.quantity or 0) if order_item else 0,
                    "sku": (
                        order_item.variant.sku
                        if order_item and order_item.variant
                        else (
                            order_item.product.sku
                            if order_item and order_item.product
                            else None
                        )
                    ),
                    "image_url": _order_item_image_url(order_item),
                },
                "agent": {
                    "name": item.logistics_agent_name,
                    "phone": item.logistics_agent_phone,
                    "assigned_at": item.logistics_assigned_at,
                },
                "pickup": {
                    "time": item.customer_picked_up_at,
                },
                "supplier_delivery": {
                    "time": item.supplier_received_at,
                },
                "completion_image_url": item.completion_image_url,
                "logistics_notes": item.logistics_notes,
            }
        )

    return data


class ReturnService:
    @staticmethod
    def _notify_parties(
        return_request, event_title, customer_message, supplier_message, admin_message
    ):
        order = return_request.order
        order_item = return_request.order_item
        supplier = _supplier_for_item(order_item)

        callbacks = [
            (
                "customer",
                lambda: NotificationService.create(
                    account_id=order.account_id,
                    title=event_title,
                    message=customer_message,
                    notification_type=NotificationType.ORDER,
                    dedupe_key=f"return:{return_request.id}:customer:{return_request.status}",
                ),
            ),
            (
                "admin",
                lambda: AdminNotificationService.notify(
                    title=event_title,
                    message=admin_message,
                    notification_type="LOGISTICS",
                    dedupe_key=f"return:{return_request.id}:admin:{return_request.status}",
                ),
            ),
        ]
        if supplier:
            callbacks.append(
                (
                    "supplier",
                    lambda: NotificationService.create(
                        account_id=supplier.id,
                        title=event_title,
                        message=supplier_message,
                        notification_type=NotificationType.ORDER,
                        dedupe_key=f"return:{return_request.id}:supplier:{supplier.id}:{return_request.status}",
                    ),
                )
            )

        for party, callback in callbacks:
            try:
                callback()
                db.session.commit()
            except Exception:
                current_app.logger.exception(
                    "Return notification failed for %s on return %s",
                    party,
                    return_request.id,
                )
                db.session.rollback()

        try:
            NotificationService.notify_logistics(
                title=event_title,
                message=admin_message,
                dedupe_key_prefix=f"return:{return_request.id}:logistics:{return_request.status}",
            )
            db.session.commit()
        except Exception:
            current_app.logger.exception(
                "Return logistics notification failed for return %s",
                return_request.id,
            )
            db.session.rollback()

    @staticmethod
    def create(account_id, order_id, order_item_id, reason):
        if not order_id or not order_item_id:
            raise ValueError("Order and order item are required.")

        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("A return reason is required.")
        if len(reason) > 2000:
            raise ValueError("Return reason is too long.")

        order = Order.query.filter_by(id=int(order_id), account_id=account_id).first()
        if not order:
            raise ValueError("Order not found.")
        if order.status != OrderStatus.DELIVERED:
            raise ValueError("Returns can only be requested after delivery.")

        order_item = OrderItem.query.filter_by(
            id=int(order_item_id), order_id=order.id
        ).first()
        if not order_item:
            raise ValueError("Order item not found.")

        existing = ReturnRequest.query.filter(
            ReturnRequest.order_item_id == order_item.id,
            ReturnRequest.status.in_(ACTIVE_RETURN_STATUSES),
        ).first()
        if existing:
            raise ValueError(
                f"A return request is already active for this item (Return #{existing.id})."
            )

        item = ReturnRequest(
            account_id=account_id,
            order_id=order.id,
            order_item_id=order_item.id,
            reason=reason,
            status="REQUESTED",
        )
        db.session.add(item)
        OrderEventService.add(
            order,
            "RETURN_REQUESTED",
            "Return requested",
            f"A return was requested for order item #{order_item.id}.",
        )
        db.session.commit()

        ReturnService._notify_parties(
            item,
            "Return request submitted",
            f"Your return request for order #{order.id} was submitted and is now in the reverse-logistics queue.",
            f"A return request was created for order #{order.id}, item #{order_item.id}. Please prepare for the returned item.",
            f"Return #{item.id} for order #{order.id} has entered reverse logistics.",
        )
        return _serialize(item)

    @staticmethod
    def list_for_customer(account_id):
        items = (
            ReturnRequest.query.filter_by(account_id=account_id)
            .order_by(ReturnRequest.created_at.desc())
            .all()
        )
        return [_serialize(item) for item in items]

    @staticmethod
    def cancel(account_id, return_id):
        item = ReturnRequest.query.filter_by(
            id=return_id, account_id=account_id
        ).first()
        if not item:
            raise ValueError("Return request not found.")
        if item.status not in {"REQUESTED"}:
            raise ValueError("This return request can no longer be cancelled.")
        item.status = "CANCELLED"
        item.resolved_at = datetime.utcnow()
        db.session.commit()
        return _serialize(item)

    @staticmethod
    def list_for_logistics():
        items = (
            ReturnRequest.query.filter(ReturnRequest.status.in_(ACTIVE_RETURN_STATUSES))
            .order_by(ReturnRequest.created_at.desc())
            .all()
        )
        return [_serialize(item, include_logistics=True) for item in items]

    @staticmethod
    def get_for_logistics(return_id):
        item = ReturnRequest.query.get(return_id)
        if not item:
            return None
        return _serialize(item, include_logistics=True)

    @staticmethod
    def assign_pickup(return_id, agent_name, agent_phone, notes=""):
        item = ReturnRequest.query.filter_by(id=return_id).with_for_update().first()
        if not item:
            return None
        if item.status not in LOGISTICS_ASSIGNABLE_STATUSES:
            raise ValueError("This return is no longer waiting for a pickup agent.")
        agent_name = str(agent_name or "").strip()
        agent_phone = str(agent_phone or "").strip()
        if len(agent_name) < 2:
            raise ValueError("Agent name is required.")
        if len(agent_phone) < 7:
            raise ValueError("A valid agent phone number is required.")

        item.status = "PICKUP_ASSIGNED"
        item.logistics_agent_name = agent_name
        item.logistics_agent_phone = agent_phone
        item.logistics_assigned_at = datetime.utcnow()
        if notes.strip():
            item.logistics_notes = notes.strip()

        OrderEventService.add(
            item.order,
            "RETURN_PICKUP_ASSIGNED",
            "Return pickup assigned",
            f"Reverse-logistics agent {agent_name} was assigned to collect return #{item.id}.",
        )
        db.session.commit()

        ReturnService._notify_parties(
            item,
            "Return pickup assigned",
            f"A pickup agent ({agent_name}) has been assigned to collect return #{item.id}.",
            f"Return #{item.id} has been assigned to {agent_name} for customer pickup.",
            f"Return #{item.id} is assigned to {agent_name} for pickup from the customer.",
        )
        return _serialize(item, include_logistics=True)

    @staticmethod
    def mark_picked_up(return_id, notes=""):
        item = ReturnRequest.query.filter_by(id=return_id).with_for_update().first()
        if not item:
            return None
        if item.status != "PICKUP_ASSIGNED":
            raise ValueError("Assign a pickup agent before collecting this return.")
        if not item.logistics_agent_name:
            raise ValueError("A pickup agent is required before collection.")

        item.status = "IN_TRANSIT_TO_SUPPLIER"
        item.customer_picked_up_at = datetime.utcnow()
        if notes.strip():
            item.logistics_notes = notes.strip()

        OrderEventService.add(
            item.order,
            "RETURN_PICKED_UP",
            "Return item picked up",
            f"Return #{item.id} was collected from the customer and is travelling back to the supplier.",
        )
        db.session.commit()

        ReturnService._notify_parties(
            item,
            "Return picked up",
            f"Return #{item.id} has been picked up from you and is now travelling back to the supplier.",
            f"Return #{item.id} has been picked up from the customer and is now in transit to the supplier.",
            f"Return #{item.id} has been picked up and is in transit to the supplier.",
        )
        return _serialize(item, include_logistics=True)

    @staticmethod
    def deliver_to_supplier(return_id, notes="", completion_photo=None):
        uploaded_public_id = None
        committed = False
        item = ReturnRequest.query.filter_by(id=return_id).with_for_update().first()
        if not item:
            return None

        try:
            if item.status != "IN_TRANSIT_TO_SUPPLIER":
                raise ValueError(
                    "The return must be picked up before it can be delivered to the supplier."
                )
            if not completion_photo or not getattr(completion_photo, "filename", ""):
                raise ValueError(
                    "A completion photo of the returned product is required."
                )

            try:
                upload = UploadService.upload(
                    completion_photo,
                    folder=f"clipcart/logistics/returns/{return_id}",
                )
            except Exception:
                current_app.logger.exception(
                    "Return completion photo upload failed for return %s", return_id
                )
                raise ValueError(
                    "The return photo could not be uploaded. Please try again."
                )

            uploaded_public_id = upload["public_id"]
            item.completion_image_url = upload["image_url"]
            item.completion_image_public_id = upload["public_id"]
            item.status = "RECEIVED"
            item.supplier_received_at = datetime.utcnow()
            item.resolved_at = item.supplier_received_at
            if notes.strip():
                item.logistics_notes = notes.strip()
            item.resolution_note = f"Return item delivered to supplier by {item.logistics_agent_name or 'logistics'}."

            OrderEventService.add(
                item.order,
                "RETURN_DELIVERED_TO_SUPPLIER",
                "Return delivered to supplier",
                f"Return #{item.id} was delivered to the supplier and reverse logistics is complete.",
            )
            db.session.commit()
            committed = True

            ReturnService._notify_parties(
                item,
                "Return delivered to supplier",
                f"Return #{item.id} has reached the supplier. The reverse-logistics movement is complete.",
                f"Return #{item.id} has been delivered to you by logistics and is ready for your return-processing workflow.",
                f"Return #{item.id} has been delivered to the supplier. Reverse logistics is complete.",
            )
            return _serialize(item, include_logistics=True)
        except Exception:
            db.session.rollback()
            if uploaded_public_id and not committed:
                try:
                    from app.services.cloudinary_service import CloudinaryService

                    CloudinaryService.delete_image(uploaded_public_id)
                except Exception:
                    current_app.logger.exception(
                        "Failed to clean up return completion photo for return %s",
                        return_id,
                    )
            raise
