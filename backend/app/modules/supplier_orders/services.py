from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.modules.accounts.models import Account
from app.modules.notifications.enums import NotificationType
from app.modules.notifications.models import Notification
from app.modules.notifications.services import NotificationService
from app.modules.admin.services import AdminNotificationService
from app.modules.order_events.services import OrderEventService
from app.modules.order_items.models import OrderItem
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.modules.product_variants.models import ProductVariant
from app.modules.products.models import Product
from app.modules.uploads.services import UploadService
from app.modules.returns.models import ReturnRequest
from app.modules.supplier_orders.enums import DeliveryStatus, PickupStatus

from .models import DeliveryAssignment
from .repository import DeliveryAssignmentRepository


class DeliveryAssignmentService:
    VISIBLE_ORDER_STATUSES = {
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    }

    ACTIVE_ORDER_STATUSES = {
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.OUT_FOR_DELIVERY,
    }

    @staticmethod
    def _eligible_order(order):
        return bool(
            order and order.status in DeliveryAssignmentService.VISIBLE_ORDER_STATUSES
        )

    @staticmethod
    def _stage(order, assignment):
        if assignment.delivery_status == DeliveryStatus.DELIVERED:
            return "DELIVERED", "Delivered"
        if assignment.delivery_status == DeliveryStatus.FAILED:
            return "FAILED", "Failed delivery"
        if assignment.delivery_status == DeliveryStatus.OUT_FOR_DELIVERY:
            return "OUT_FOR_DELIVERY", "Out for delivery"
        if assignment.delivery_status == DeliveryStatus.IN_TRANSIT:
            return "IN_TRANSIT", "In transit"
        if assignment.pickup_status == PickupStatus.ASSIGNED:
            return "PICKUP_ASSIGNED", "Pickup assigned"
        if assignment.pickup_status == PickupStatus.PENDING:
            return "AWAITING_PICKUP", "Awaiting pickup"
        if assignment.pickup_status == PickupStatus.PICKED_UP:
            return "IN_TRANSIT", "In transit"
        return "AWAITING_PICKUP", "Awaiting pickup"

    @staticmethod
    def _pending_action(order, assignment):
        stage, _ = DeliveryAssignmentService._stage(order, assignment)
        return {
            "AWAITING_PICKUP": "Assign pickup agent",
            "PICKUP_ASSIGNED": "Mark pickup",
            "IN_TRANSIT": "Move to out for delivery",
            "OUT_FOR_DELIVERY": "Complete delivery or record attempt",
            "FAILED": "Review failure and retry/reschedule",
            "DELIVERED": None,
        }.get(stage)

    @staticmethod
    def _serialize_assignment(assignment, include_order=False):
        order = assignment.order
        stage, stage_label = DeliveryAssignmentService._stage(order, assignment)
        data = {
            "id": assignment.id,
            "order_id": order.id if order else assignment.order_id,
            "order_status": order.status.value if order else None,
            "stage": stage,
            "stage_label": stage_label,
            "pending_action": DeliveryAssignmentService._pending_action(
                order, assignment
            ),
            "customer": {
                "name": order.delivery_full_name if order else None,
                "phone": order.delivery_phone if order else None,
            },
            "destination": {
                "address_line_1": order.delivery_address_line_1 if order else None,
                "address_line_2": order.delivery_address_line_2 if order else None,
                "landmark": order.delivery_landmark if order else None,
                "city": order.delivery_city if order else None,
                "state": order.delivery_state if order else None,
                "postal_code": order.delivery_postal_code if order else None,
                "country": order.delivery_country if order else None,
            },
            "agent": {
                "name": assignment.agent_name,
                "phone": assignment.agent_phone,
                "assigned_at": assignment.assigned_at,
                "assigned_by_id": assignment.assigned_by_id,
            },
            "pickup": {
                "status": assignment.pickup_status.value,
                "time": assignment.pickup_time,
            },
            "delivery": {
                "status": assignment.delivery_status.value,
                "time": assignment.delivery_time,
                "out_for_delivery_time": assignment.out_for_delivery_time,
                "attempts": int(assignment.delivery_attempts or 0),
                "last_attempt_at": assignment.last_attempt_at,
                "last_attempt_reason": assignment.last_attempt_reason,
                "failed_reason": assignment.failed_reason,
                "next_action": assignment.next_action,
            },
            "notes": assignment.notes,
            "customer_delivery_notes": assignment.customer_delivery_notes,
            "proof_of_delivery_reference": assignment.proof_of_delivery_reference,
            "proof_of_delivery_image_url": assignment.proof_of_delivery_image_url,
            "created_at": assignment.created_at,
            "updated_at": assignment.updated_at,
        }
        if include_order and order:
            data["created_order_at"] = order.created_at
            data["items"] = [
                {
                    "id": item.id,
                    "product_name": item.product_name_snapshot
                    or (item.product.name if item.product else "Product"),
                    "variant": item.variant_value_snapshot
                    or (item.variant.value if item.variant else None),
                    "quantity": int(item.quantity or 0),
                    "sku": (
                        item.variant.sku
                        if item.variant
                        else (item.product.sku if item.product else None)
                    ),
                }
                for item in order.items
            ]
            data["timeline"] = (
                [
                    OrderEventService.serialize(event)
                    for event in order.events.order_by("occurred_at", "id").all()
                ]
                if getattr(order, "events", None)
                else []
            )
        return data

    @staticmethod
    def _visible_assignment_query():
        return DeliveryAssignment.query.join(Order).filter(
            Order.status.in_(DeliveryAssignmentService.VISIBLE_ORDER_STATUSES)
        )

    @staticmethod
    def get_dashboard(account_id):
        active_query = DeliveryAssignmentService._visible_assignment_query()
        awaiting_pickup = active_query.filter(
            Order.status == OrderStatus.PROCESSING,
            DeliveryAssignment.pickup_status == PickupStatus.PENDING,
        ).count()
        pickup_assigned = active_query.filter(
            Order.status == OrderStatus.PROCESSING,
            DeliveryAssignment.pickup_status == PickupStatus.ASSIGNED,
        ).count()
        picked_up = active_query.filter(
            DeliveryAssignment.pickup_status == PickupStatus.PICKED_UP
        ).count()
        in_transit = active_query.filter(
            DeliveryAssignment.delivery_status == DeliveryStatus.IN_TRANSIT
        ).count()
        out_for_delivery = active_query.filter(
            DeliveryAssignment.delivery_status == DeliveryStatus.OUT_FOR_DELIVERY
        ).count()
        failed = active_query.filter(
            DeliveryAssignment.delivery_status == DeliveryStatus.FAILED
        ).count()

        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        delivered_today = active_query.filter(
            DeliveryAssignment.delivery_status == DeliveryStatus.DELIVERED,
            DeliveryAssignment.delivery_time >= today_start,
        ).count()

        attempts_today = (
            active_query.filter(DeliveryAssignment.last_attempt_at >= today_start)
            .with_entities(
                func.coalesce(func.sum(DeliveryAssignment.delivery_attempts), 0)
            )
            .scalar()
        )

        workload = active_query.filter(
            Order.status.in_(DeliveryAssignmentService.ACTIVE_ORDER_STATUSES)
        ).count()

        awaiting_supplier_handoff = Order.query.filter(
            Order.status == OrderStatus.PAID
        ).count()

        unread = Notification.query.filter_by(
            account_id=account_id, is_read=False
        ).count()

        recent_alerts = (
            Notification.query.filter_by(account_id=account_id)
            .order_by(Notification.created_at.desc())
            .limit(8)
            .all()
        )

        active_returns = ReturnRequest.query.filter(
            ReturnRequest.status.in_(
                {
                    "REQUESTED",
                    "PICKUP_ASSIGNED",
                    "PICKED_UP",
                    "IN_TRANSIT",
                    "OUT_FOR_DELIVERY",
                    "FAILED",
                }
            )
        ).count()

        return {
            "metrics": {
                "new_orders_awaiting_processing": awaiting_supplier_handoff,
                "awaiting_pickup": awaiting_pickup,
                "pickup_assigned": pickup_assigned,
                "picked_up": picked_up,
                "in_transit": in_transit,
                "out_for_delivery": out_for_delivery,
                "delivered_today": delivered_today,
                "failed_deliveries": failed,
                "attempts_today": int(attempts_today or 0),
                "current_workload": workload,
                "unread_alerts": unread,
                "active_returns": active_returns,
            },
            "recent_alerts": [
                DeliveryAssignmentService.serialize_notification(n)
                for n in recent_alerts
            ],
        }

    @staticmethod
    def get_queue(
        search=None, stage=None, status=None, date=None, agent=None, pending_action=None
    ):
        query = DeliveryAssignmentService._visible_assignment_query()

        stage = str(stage or "").strip().upper()
        status = str(status or "").strip().upper()
        search = str(search or "").strip()
        agent = str(agent or "").strip()

        if not stage and not status:
            query = query.filter(
                Order.status.in_(DeliveryAssignmentService.ACTIVE_ORDER_STATUSES)
                | (DeliveryAssignment.delivery_status == DeliveryStatus.FAILED)
            )

        if status:
            if status == "AWAITING_PICKUP":
                query = query.filter(
                    DeliveryAssignment.pickup_status == PickupStatus.PENDING,
                    Order.status == OrderStatus.PROCESSING,
                )
            elif status == "PICKUP_ASSIGNED":
                query = query.filter(
                    DeliveryAssignment.pickup_status == PickupStatus.ASSIGNED
                )
            elif status == "PICKED_UP":
                query = query.filter(
                    DeliveryAssignment.pickup_status == PickupStatus.PICKED_UP
                )
            elif status in DeliveryStatus.__members__:
                query = query.filter(
                    DeliveryAssignment.delivery_status == DeliveryStatus[status]
                )
            elif status in OrderStatus.__members__:
                query = query.filter(Order.status == OrderStatus[status])
            else:
                raise ValueError("Invalid logistics status filter.")

        if stage:
            stage_to_filters = {
                "AWAITING_PICKUP": (
                    DeliveryAssignment.pickup_status == PickupStatus.PENDING,
                    Order.status == OrderStatus.PROCESSING,
                ),
                "PICKUP_ASSIGNED": (
                    DeliveryAssignment.pickup_status == PickupStatus.ASSIGNED,
                ),
                "IN_TRANSIT": (
                    DeliveryAssignment.delivery_status == DeliveryStatus.IN_TRANSIT,
                ),
                "OUT_FOR_DELIVERY": (
                    DeliveryAssignment.delivery_status
                    == DeliveryStatus.OUT_FOR_DELIVERY,
                ),
                "DELIVERED": (
                    DeliveryAssignment.delivery_status == DeliveryStatus.DELIVERED,
                ),
                "FAILED": (
                    DeliveryAssignment.delivery_status == DeliveryStatus.FAILED,
                ),
            }
            if stage not in stage_to_filters:
                raise ValueError("Invalid logistics stage filter.")
            for condition in stage_to_filters[stage]:
                query = query.filter(condition)

        if date:
            try:
                day = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date filter must use YYYY-MM-DD.")
            next_day = day + timedelta(days=1)
            query = query.filter(Order.created_at >= day, Order.created_at < next_day)

        if agent:
            term = f"%{agent}%"
            query = query.filter(
                DeliveryAssignment.agent_name.ilike(term)
                | DeliveryAssignment.agent_phone.ilike(term)
            )

        if search:
            like = f"%{search}%"
            filters = [
                Order.delivery_full_name.ilike(like),
                Order.delivery_phone.ilike(like),
                Order.delivery_city.ilike(like),
                Order.delivery_postal_code.ilike(like),
            ]
            if search.isdigit():
                filters.append(Order.id == int(search))
            query = query.filter(
                *(
                    [filters[0]]
                    if len(filters) == 1
                    else (
                        filters[0] | filters[1] | filters[2] | filters[3] | filters[4]
                    )
                )
            )

        rows = query.order_by(Order.created_at.desc(), Order.id.desc()).all()
        result = []
        for assignment in rows:
            item = DeliveryAssignmentService._serialize_assignment(assignment)
            if pending_action:
                expected = str(item.get("pending_action") or "").strip().upper()
                if str(pending_action).strip().upper() not in expected:
                    continue
            result.append(item)
        return result

    @staticmethod
    def get_for_order(order_id):
        order = Order.query.get(order_id)
        if not DeliveryAssignmentService._eligible_order(order):
            return None

        assignment = DeliveryAssignmentRepository.get_by_order_id(order_id)
        if not assignment:
            if order.status != OrderStatus.PROCESSING:
                return None
            assignment = DeliveryAssignmentRepository.get_or_create(order_id)
            db.session.commit()

        return DeliveryAssignmentService._serialize_assignment(
            assignment, include_order=True
        )

    @staticmethod
    def _get_locked(order_id):
        order = Order.query.filter_by(id=order_id).with_for_update().first()
        if not DeliveryAssignmentService._eligible_order(order):
            return None, None
        assignment = (
            DeliveryAssignment.query.filter_by(order_id=order_id)
            .with_for_update()
            .first()
        )
        if not assignment:
            if order.status != OrderStatus.PROCESSING:
                return None, None
            assignment = DeliveryAssignmentRepository.get_or_create(order_id)
        return order, assignment

    @staticmethod
    def assign_agent(order_id, agent_name, agent_phone, assigned_by_id):
        try:
            order, assignment = DeliveryAssignmentService._get_locked(order_id)
            if not order or not assignment:
                return None
            if order.status != OrderStatus.PROCESSING:
                raise ValueError("Pickup can only be assigned after supplier handoff.")
            if assignment.pickup_status == PickupStatus.PICKED_UP:
                raise ValueError("The order has already been picked up.")

            was_reassignment = bool(assignment.agent_name or assignment.agent_phone)
            assignment.agent_name = agent_name.strip()
            assignment.agent_phone = agent_phone.strip()
            assignment.assigned_by_id = assigned_by_id
            assignment.assigned_at = datetime.utcnow()
            assignment.pickup_status = PickupStatus.ASSIGNED

            OrderEventService.add(
                order,
                "DELIVERY_REASSIGNED" if was_reassignment else "DELIVERY_ASSIGNED",
                (
                    "Delivery agent reassigned"
                    if was_reassignment
                    else "Delivery agent assigned"
                ),
                f"Delivery agent {assignment.agent_name} was assigned for order #{order.id}.",
            )
            NotificationService.notify_logistics(
                title="Delivery assignment updated",
                message=(
                    f"Order #{order.id} was "
                    f"{'reassigned' if was_reassignment else 'assigned'} to "
                    f"{assignment.agent_name}."
                ),
                dedupe_key_prefix=f"order:{order.id}:logistics:assignment:{assignment.assigned_at.timestamp()}",
            )
            db.session.commit()
            return DeliveryAssignmentService.get_for_order(order_id)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def mark_picked_up(order_id):
        try:
            order, assignment = DeliveryAssignmentService._get_locked(order_id)
            if not order or not assignment:
                return None
            if assignment.pickup_status != PickupStatus.ASSIGNED:
                raise ValueError("Assign a delivery agent before marking the pickup.")
            if order.status != OrderStatus.PROCESSING:
                raise ValueError("Order is not awaiting supplier handoff/pickup.")

            assignment.pickup_status = PickupStatus.PICKED_UP
            assignment.pickup_time = datetime.utcnow()
            assignment.delivery_status = DeliveryStatus.IN_TRANSIT

            order.status = OrderStatus.SHIPPED
            OrderEventService.add(
                order,
                "PICKED_UP",
                "Order picked up",
                f"Order #{order.id} was picked up and is in transit.",
            )
            OrderEventService.add(
                order,
                "SHIPPED",
                "Order shipped",
                f"Order #{order.id} has been shipped and is in transit.",
            )
            db.session.commit()

            try:
                AdminNotificationService.delivery_updated(
                    order.id, "order picked up and is in transit"
                )
            except Exception:
                db.session.rollback()

            NotificationService.create(
                account_id=order.account_id,
                title="Order picked up",
                message=f"Order #{order.id} has been picked up and is on its way.",
                notification_type=NotificationType.ORDER,
                dedupe_key=f"order:{order.id}:customer:picked-up",
            )
            for item in order.items:
                supplier_id = item.product.seller_id if item.product else None
                if supplier_id:
                    NotificationService.create(
                        account_id=supplier_id,
                        title="Order shipped",
                        message=f"Order #{order.id} has been picked up and is now in transit.",
                        notification_type=NotificationType.ORDER,
                        dedupe_key=f"order:{order.id}:supplier:{supplier_id}:shipped",
                    )
            return DeliveryAssignmentService.get_for_order(order_id)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def mark_out_for_delivery(order_id):
        try:
            order, assignment = DeliveryAssignmentService._get_locked(order_id)
            if not order or not assignment:
                return None
            if assignment.delivery_status != DeliveryStatus.IN_TRANSIT:
                raise ValueError(
                    "Order must be in transit before marking out for delivery."
                )
            if not assignment.agent_name:
                raise ValueError(
                    "Assign a delivery agent before dispatching the order."
                )

            assignment.delivery_status = DeliveryStatus.OUT_FOR_DELIVERY
            assignment.out_for_delivery_time = datetime.utcnow()
            order.status = OrderStatus.OUT_FOR_DELIVERY
            OrderEventService.add(
                order,
                "OUT_FOR_DELIVERY",
                "Out for delivery",
                f"Order #{order.id} is out for delivery.",
            )
            db.session.commit()

            try:
                AdminNotificationService.delivery_updated(
                    order.id, "order is out for delivery"
                )
            except Exception:
                db.session.rollback()

            NotificationService.create(
                account_id=order.account_id,
                title="Out for delivery",
                message=f"Order #{order.id} is out for delivery today.",
                notification_type=NotificationType.ORDER,
                dedupe_key=f"order:{order.id}:customer:ofd",
            )
            return DeliveryAssignmentService.get_for_order(order_id)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def record_attempt(order_id, reason, notes=""):
        try:
            order, assignment = DeliveryAssignmentService._get_locked(order_id)
            if not order or not assignment:
                return None
            if assignment.delivery_status != DeliveryStatus.OUT_FOR_DELIVERY:
                raise ValueError(
                    "A delivery attempt can only be recorded while out for delivery."
                )

            now = datetime.utcnow()
            assignment.delivery_attempts = int(assignment.delivery_attempts or 0) + 1
            assignment.last_attempt_at = now
            assignment.last_attempt_reason = reason.strip()
            if notes.strip():
                assignment.notes = notes.strip()
            OrderEventService.add(
                order,
                "DELIVERY_ATTEMPT",
                "Delivery attempt recorded",
                reason.strip(),
            )
            NotificationService.notify_logistics(
                title="Delivery attempt recorded",
                message=f"Order #{order.id}: {reason.strip()}",
                dedupe_key_prefix=f"order:{order.id}:logistics:attempt:{assignment.delivery_attempts}",
            )
            db.session.commit()
            NotificationService.create(
                account_id=order.account_id,
                title="Delivery attempt update",
                message=f"A delivery attempt was recorded for order #{order.id}.",
                notification_type=NotificationType.ORDER,
            )
            return DeliveryAssignmentService.get_for_order(order_id)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def mark_delivered(
        order_id,
        notes="",
        customer_delivery_notes="",
        proof_of_delivery_reference="",
        completion_photo=None,
    ):
        uploaded_public_id = None
        committed = False
        try:
            order, assignment = DeliveryAssignmentService._get_locked(order_id)
            if not order or not assignment:
                return None
            if assignment.delivery_status != DeliveryStatus.OUT_FOR_DELIVERY:
                raise ValueError(
                    "Order must be out for delivery before it can be delivered."
                )
            if not completion_photo or not getattr(completion_photo, "filename", ""):
                raise ValueError(
                    "A completion photo of the delivered product is required."
                )

            try:
                upload = UploadService.upload(
                    completion_photo,
                    folder=f"clipcart/logistics/delivered/{order_id}",
                )
            except Exception:
                current_app.logger.exception(
                    "Delivery completion photo upload failed for order %s", order_id
                )
                raise ValueError(
                    "The delivery photo could not be uploaded. Please try again."
                )

            uploaded_public_id = upload["public_id"]
            assignment.proof_of_delivery_image_url = upload["image_url"]
            assignment.proof_of_delivery_image_public_id = upload["public_id"]
            assignment.delivery_status = DeliveryStatus.DELIVERED
            assignment.delivery_time = datetime.utcnow()
            assignment.next_action = None
            assignment.failed_reason = None
            if notes.strip():
                assignment.notes = notes.strip()
            if customer_delivery_notes.strip():
                assignment.customer_delivery_notes = customer_delivery_notes.strip()
            if proof_of_delivery_reference.strip():
                assignment.proof_of_delivery_reference = (
                    proof_of_delivery_reference.strip()
                )

            order.status = OrderStatus.DELIVERED
            OrderEventService.add(
                order,
                "DELIVERED",
                "Order delivered",
                f"Order #{order.id} has been delivered.",
            )
            db.session.commit()
            committed = True

            try:
                AdminNotificationService.delivery_updated(order.id, "order delivered")
            except Exception:
                db.session.rollback()

            NotificationService.create(
                account_id=order.account_id,
                title="Order delivered",
                message=f"Order #{order.id} has been delivered.",
                notification_type=NotificationType.ORDER,
                dedupe_key=f"order:{order.id}:customer:delivered",
            )
            return DeliveryAssignmentService.get_for_order(order_id)
        except Exception:
            db.session.rollback()
            if uploaded_public_id and not committed:
                try:
                    from app.services.cloudinary_service import CloudinaryService

                    CloudinaryService.delete_image(uploaded_public_id)
                except Exception:
                    current_app.logger.exception(
                        "Failed to clean up delivery completion photo for order %s",
                        order_id,
                    )
            raise

    @staticmethod
    def mark_failed(order_id, reason, next_action, notes=""):
        try:
            order, assignment = DeliveryAssignmentService._get_locked(order_id)
            if not order or not assignment:
                return None
            if assignment.delivery_status != DeliveryStatus.OUT_FOR_DELIVERY:
                raise ValueError(
                    "A delivery failure can only be recorded while out for delivery."
                )

            now = datetime.utcnow()
            assignment.delivery_status = DeliveryStatus.FAILED
            assignment.delivery_attempts = int(assignment.delivery_attempts or 0) + 1
            assignment.last_attempt_at = now
            assignment.last_attempt_reason = reason.strip()
            assignment.failed_reason = reason.strip()
            assignment.next_action = next_action.strip()
            if notes.strip():
                assignment.notes = notes.strip()

            OrderEventService.add(
                order,
                "DELIVERY_FAILED",
                "Delivery attempt failed",
                f"{reason.strip()} Next action: {next_action.strip()}",
            )
            NotificationService.notify_logistics(
                title="Urgent delivery issue",
                message=(
                    f"Order #{order.id} failed delivery: {reason.strip()}. "
                    f"Next action: {next_action.strip()}."
                ),
                dedupe_key_prefix=f"order:{order.id}:logistics:failed:{assignment.delivery_attempts}",
            )
            db.session.commit()

            try:
                AdminNotificationService.delivery_updated(
                    order.id, "delivery attempt failed"
                )
            except Exception:
                db.session.rollback()

            NotificationService.create(
                account_id=order.account_id,
                title="Delivery attempt failed",
                message=f"We could not complete delivery of order #{order.id}.",
                notification_type=NotificationType.ORDER,
                dedupe_key=f"order:{order.id}:customer:delivery-failed:{assignment.delivery_attempts}",
            )
            return DeliveryAssignmentService.get_for_order(order_id)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def retry_failed(order_id, notes=""):
        try:
            order, assignment = DeliveryAssignmentService._get_locked(order_id)
            if not order or not assignment:
                return None
            if assignment.delivery_status != DeliveryStatus.FAILED:
                raise ValueError("Only failed deliveries can be retried.")
            if not assignment.agent_name:
                raise ValueError(
                    "Assign a delivery agent before retrying the delivery."
                )

            assignment.delivery_status = DeliveryStatus.IN_TRANSIT
            assignment.next_action = "Retry in transit"
            if notes.strip():
                assignment.notes = notes.strip()
            order.status = OrderStatus.SHIPPED

            OrderEventService.add(
                order,
                "DELIVERY_RETRY",
                "Delivery retry started",
                f"Order #{order.id} was moved back to in transit for another delivery attempt.",
            )
            db.session.commit()
            return DeliveryAssignmentService.get_for_order(order_id)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def _item_preview(item):
        product = item.product
        variant = item.variant

        image_url = None
        if variant and getattr(variant, "images", None):
            variant_images = list(variant.images)
            image = next((row for row in variant_images if row.is_thumbnail), None)
            image = image or (variant_images[0] if variant_images else None)
            image_url = image.image_url if image else None

        if not image_url and product and getattr(product, "images", None):
            product_images = [row for row in product.images if row.variant_id is None]
            image = next((row for row in product_images if row.is_thumbnail), None)
            image = image or (product_images[0] if product_images else None)
            image_url = image.image_url if image else None

        return {
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product_name_snapshot
            or (product.name if product else "Product"),
            "variant": item.variant_value_snapshot
            or (variant.value if variant else None),
            "quantity": int(item.quantity or 0),
            "sku": variant.sku if variant else (product.sku if product else None),
            "image_url": image_url,
        }

    @staticmethod
    def get_completed_history(limit=100):
        safe_limit = min(max(int(limit or 100), 1), 200)

        delivered_rows = (
            DeliveryAssignment.query.join(Order)
            .filter(DeliveryAssignment.delivery_status == DeliveryStatus.DELIVERED)
            .options(
                joinedload(DeliveryAssignment.order)
                .selectinload(Order.items)
                .joinedload(OrderItem.product)
                .selectinload(Product.images),
                joinedload(DeliveryAssignment.order)
                .selectinload(Order.items)
                .joinedload(OrderItem.variant)
                .selectinload(ProductVariant.images),
            )
            .order_by(
                DeliveryAssignment.delivery_time.desc(), DeliveryAssignment.id.desc()
            )
            .limit(safe_limit)
            .all()
        )

        returned_rows = (
            ReturnRequest.query.filter(ReturnRequest.status == "RECEIVED")
            .options(
                joinedload(ReturnRequest.order),
                joinedload(ReturnRequest.order_item)
                .joinedload(OrderItem.product)
                .joinedload(Product.seller)
                .joinedload(Account.seller_verification),
                joinedload(ReturnRequest.order_item)
                .joinedload(OrderItem.product)
                .selectinload(Product.images),
                joinedload(ReturnRequest.order_item)
                .joinedload(OrderItem.variant)
                .selectinload(ProductVariant.images),
            )
            .order_by(
                ReturnRequest.supplier_received_at.desc(), ReturnRequest.id.desc()
            )
            .limit(safe_limit)
            .all()
        )

        delivered = []
        for assignment in delivered_rows:
            order = assignment.order
            delivered.append(
                {
                    "type": "DELIVERED",
                    "id": assignment.id,
                    "order_id": order.id if order else assignment.order_id,
                    "customer": {
                        "name": order.delivery_full_name if order else None,
                        "phone": order.delivery_phone if order else None,
                    },
                    "destination": {
                        "city": order.delivery_city if order else None,
                        "state": order.delivery_state if order else None,
                        "postal_code": order.delivery_postal_code if order else None,
                    },
                    "agent": {
                        "name": assignment.agent_name,
                        "phone": assignment.agent_phone,
                    },
                    "delivered_at": assignment.delivery_time,
                    "proof_image_url": assignment.proof_of_delivery_image_url,
                    "proof_reference": assignment.proof_of_delivery_reference,
                    "customer_delivery_notes": assignment.customer_delivery_notes,
                    "items": (
                        [
                            DeliveryAssignmentService._item_preview(item)
                            for item in order.items
                        ]
                        if order
                        else []
                    ),
                }
            )

        returned = []
        for item in returned_rows:
            order = item.order
            order_item = item.order_item
            product = order_item.product if order_item else None
            supplier = product.seller if product else None
            verification = (
                getattr(supplier, "seller_verification", None) if supplier else None
            )
            returned.append(
                {
                    "type": "RETURNED",
                    "id": item.id,
                    "return_id": item.id,
                    "order_id": item.order_id,
                    "customer": {
                        "name": order.delivery_full_name if order else None,
                        "phone": order.delivery_phone if order else None,
                    },
                    "supplier": {
                        "name": supplier.full_name if supplier else None,
                        "business_name": (
                            verification.business_name if verification else None
                        ),
                        "phone": supplier.phone if supplier else None,
                    },
                    "reason": item.reason,
                    "agent": {
                        "name": item.logistics_agent_name,
                        "phone": item.logistics_agent_phone,
                    },
                    "picked_up_at": item.customer_picked_up_at,
                    "returned_at": item.supplier_received_at,
                    "completion_image_url": item.completion_image_url,
                    "item": (
                        DeliveryAssignmentService._item_preview(order_item)
                        if order_item
                        else None
                    ),
                    "resolution_note": item.resolution_note,
                }
            )

        return {"delivered": delivered, "returned": returned}

    @staticmethod
    def serialize_notification(notification):
        return {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.notification_type,
            "is_read": notification.is_read,
            "created_at": notification.created_at,
        }

    @staticmethod
    def get_notifications(account_id, unread_only=False, limit=30):
        query = Notification.query.filter_by(account_id=account_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        rows = (
            query.order_by(Notification.created_at.desc())
            .limit(min(max(limit, 1), 100))
            .all()
        )
        return [DeliveryAssignmentService.serialize_notification(n) for n in rows]
