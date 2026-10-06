import csv
from flask import current_app
import io

from datetime import datetime

from app.extensions import db
from app.modules.inventory.models import InventoryLog
from app.modules.order_events.services import OrderEventService
from app.modules.order_items.models import OrderItem
from app.modules.payments.models import Payment
from app.modules.product_variants.models import ProductVariant
from app.modules.product_images.models import ProductImage
from app.modules.products.models import Product
from app.modules.reviews.models import Review
from app.modules.stock_alerts.services import StockAlertService
from app.services.razorpay_service import RazorpayService
from app.modules.supplier_orders.models import DeliveryAssignment
from app.modules.notifications.enums import NotificationType
from app.modules.notifications.services import NotificationService
from app.modules.admin.services import AdminNotificationService
from app.modules.shiprocket.service import ShiprocketError, ShiprocketService

from .enums import OrderStatus
from .models import Order
from .repository import OrderRepository

EXCLUDED_REVENUE = {OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value}


def _item_image_map(items):
    """Return one lightweight preview URL per ordered product/variant."""
    items = list(items or [])
    product_ids = {int(item.product_id) for item in items if item.product_id}
    if not product_ids:
        return {}

    variant_ids = {int(item.variant_id) for item in items if item.variant_id}
    query = ProductImage.query.filter(ProductImage.product_id.in_(product_ids))
    if variant_ids:
        query = query.filter(
            (ProductImage.variant_id.is_(None))
            | ProductImage.variant_id.in_(variant_ids)
        )
    images = query.order_by(
        ProductImage.is_thumbnail.desc(),
        ProductImage.sort_order.asc(),
        ProductImage.id.asc(),
    ).all()

    result = {}
    for image in images:
        key = (
            (
                "variant",
                int(image.variant_id),
            )
            if image.variant_id
            else ("product", int(image.product_id))
        )
        result.setdefault(key, image.image_url)
    return result


def _item_image(item, image_map):
    if item.variant_id:
        image = image_map.get(("variant", int(item.variant_id)))
        if image:
            return image
    return image_map.get(("product", int(item.product_id)))


def _serialize_return_delivery(request):
    assignment = getattr(request, "delivery_assignment", None)
    if not assignment:
        return None
    if (
        assignment.delivery_status == "DELIVERED"
        or getattr(assignment.delivery_status, "value", None) == "DELIVERED"
    ):
        stage = "RECEIVED"
        label = "Delivered to supplier"
    elif getattr(assignment.delivery_status, "value", None) == "OUT_FOR_DELIVERY":
        stage = "OUT_FOR_DELIVERY"
        label = "Out for delivery to supplier"
    elif getattr(assignment.delivery_status, "value", None) == "IN_TRANSIT":
        stage = "IN_TRANSIT"
        label = "Returning to supplier"
    elif getattr(assignment.pickup_status, "value", None) == "ASSIGNED":
        stage = "PICKUP_ASSIGNED"
        label = "Return pickup assigned"
    elif getattr(assignment.pickup_status, "value", None) == "PICKED_UP":
        stage = "IN_TRANSIT"
        label = "Returning to supplier"
    else:
        stage = "AWAITING_PICKUP"
        label = "Awaiting return pickup"
    return {
        "stage": stage,
        "stage_label": label,
        "pending_action": {
            "AWAITING_PICKUP": "Assign pickup agent",
            "PICKUP_ASSIGNED": "Pick up from customer",
            "IN_TRANSIT": "Dispatch to supplier",
            "OUT_FOR_DELIVERY": "Deliver to supplier",
            "RECEIVED": None,
        }.get(stage),
        "agent": {
            "name": assignment.agent_name,
            "phone": assignment.agent_phone,
            "assigned_at": assignment.assigned_at,
        },
        "pickup": {
            "status": assignment.pickup_status.value,
            "time": assignment.pickup_time,
        },
        "delivery": {
            "status": assignment.delivery_status.value,
            "out_for_delivery_time": assignment.out_for_delivery_time,
            "time": assignment.delivery_time,
            "attempts": int(assignment.attempts or 0),
            "last_attempt_at": assignment.last_attempt_at,
            "last_attempt_reason": assignment.last_attempt_reason,
            "failed_reason": assignment.failed_reason,
            "next_action": assignment.next_action,
        },
        "supplier": {
            "id": assignment.supplier_id,
            "name": assignment.supplier_name,
            "business_name": assignment.supplier_business_name,
            "phone": assignment.supplier_phone,
            "address_line_1": assignment.supplier_address_line_1,
            "address_line_2": assignment.supplier_address_line_2,
            "landmark": assignment.supplier_landmark,
            "city": assignment.supplier_city,
            "state": assignment.supplier_state,
            "postal_code": assignment.supplier_postal_code,
            "country": assignment.supplier_country,
        },
    }


class OrderService:
    @staticmethod
    def _serialize_order(order, include_events=True, image_map=None, force_shiprocket_refresh=False):
        invoice = getattr(order, "invoice", None)
        image_map = image_map if image_map is not None else _item_image_map(order.items)
        return {
            "id": order.id,
            "status": order.status.value,
            "subtotal": float(order.subtotal or 0),
            "discount": float(order.discount or 0),
            "taxable_base": float(order.taxable_base or 0),
            "marketing_fee": float(order.marketing_fee or 0),
            "tax": float(order.tax or 0),
            "total": float(order.total or 0),
            "payment_id": order.payment_id,
            "payment_status": order.payment.status if order.payment else "UNKNOWN",
            "customer": {
                "name": order.customer_name,
                "email": order.customer_email,
            },
            "delivery": {
                "full_name": order.delivery_full_name,
                "phone": order.delivery_phone,
                "address_line_1": order.delivery_address_line_1,
                "address_line_2": order.delivery_address_line_2,
                "landmark": order.delivery_landmark,
                "city": order.delivery_city,
                "state": order.delivery_state,
                "postal_code": order.delivery_postal_code,
                "country": order.delivery_country,
            },
            "created_at": order.created_at,
            "cancelled_at": order.cancelled_at,
            "cancellation_reason": order.cancellation_reason,
            "invoice": (
                {
                    "id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "status": invoice.status,
                    "available": invoice.status == "GENERATED"
                    and bool(invoice.file_path),
                }
                if invoice
                else None
            ),
            "delivery_assignment": (
                {
                    "pickup_status": order.delivery_assignment.pickup_status.value,
                    "pickup_time": order.delivery_assignment.pickup_time,
                    "delivery_status": order.delivery_assignment.delivery_status.value,
                    "delivery_time": order.delivery_assignment.delivery_time,
                    "agent_name": order.delivery_assignment.agent_name,
                    "agent_phone": order.delivery_assignment.agent_phone,
                    "notes": order.delivery_assignment.notes,
                }
                if getattr(order, "delivery_assignment", None)
                else None
            ),
            "shipments": ShiprocketService.get_customer_shipments(order, force_refresh=force_shiprocket_refresh),
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product_name_snapshot
                    or (item.product.name if item.product else "Product"),
                    "image": _item_image(item, image_map),
                    "variant_id": item.variant_id,
                    "variant_name": item.variant_name_snapshot
                    or (item.variant.name if item.variant else None),
                    "variant_value": item.variant_value_snapshot
                    or (item.variant.value if item.variant else None),
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price or 0),
                    "subtotal": float(item.subtotal or 0),
                }
                for item in order.items
            ],
            "events": (
                [
                    OrderEventService.serialize(event)
                    for event in order.events.order_by("occurred_at", "id").all()
                ]
                if include_events and getattr(order, "events", None)
                else []
            ),
            "returns": [
                {
                    "id": request.id,
                    "order_item_id": request.order_item_id,
                    "reason": request.reason,
                    "status": request.status,
                    "created_at": request.created_at,
                    "updated_at": request.updated_at,
                    "resolution_note": request.resolution_note,
                    "resolved_at": request.resolved_at,
                    "delivery": _serialize_return_delivery(request),
                }
                for request in order.return_requests
            ],
        }

    @staticmethod
    def get_orders(account_id):
        orders = OrderRepository.get_by_account(account_id)
        image_map = _item_image_map([item for order in orders for item in order.items])
        return [
            OrderService._serialize_order(
                order, include_events=False, image_map=image_map
            )
            for order in orders
        ]

    @staticmethod
    def get_active_orders(account_id):
        active = {
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.OUT_FOR_DELIVERY,
        }
        orders = [
            order
            for order in OrderRepository.get_by_account(account_id)
            if order.status in active
        ]
        image_map = _item_image_map([item for order in orders for item in order.items])
        return [
            OrderService._serialize_order(
                order, include_events=False, image_map=image_map
            )
            for order in orders
        ]

    @staticmethod
    def get_order(account_id, order_id):
        order = OrderRepository.get_by_id(order_id)
        if not order or order.account_id != account_id:
            return None
        return OrderService._serialize_order(
            order, image_map=_item_image_map(order.items)
        )

    @staticmethod
    def get_tracking(account_id, order_id, *, force_refresh=False):
        order = OrderRepository.get_by_id(order_id)
        if not order or order.account_id != account_id:
            return None
        data = OrderService._serialize_order(
            order, image_map=_item_image_map(order.items), force_shiprocket_refresh=force_refresh
        )
        data["tracking"] = data["events"]
        return data

    @staticmethod
    def get_reviewable_items(account_id, product_id=None):
        query = (
            OrderItem.query.join(Order)
            .filter(
                Order.account_id == account_id, Order.status == OrderStatus.DELIVERED
            )
            .order_by(Order.created_at.desc(), OrderItem.id.desc())
        )
        if product_id:
            query = query.filter(OrderItem.product_id == product_id)

        items = []
        for item in query.all():
            if Review.query.filter_by(order_item_id=item.id).first():
                continue
            items.append(
                {
                    "order_item_id": item.id,
                    "order_id": item.order_id,
                    "product_id": item.product_id,
                    "product_name": item.product.name if item.product else "Product",
                    "variant_value": item.variant.value if item.variant else None,
                    "purchased_at": item.order.created_at,
                }
            )
        return items

    @staticmethod
    def cancel_order(account_id, order_id, reason=None):
        order = (
            Order.query.filter_by(id=order_id, account_id=account_id)
            .with_for_update()
            .first()
        )
        if not order:
            raise ValueError("Order not found.")

        if order.status == OrderStatus.CANCELLED:
            return OrderService._serialize_order(order)
        if order.status not in {OrderStatus.PAID, OrderStatus.PROCESSING}:
            raise ValueError("This order can no longer be cancelled.")

        for item in order.items:
            product = (
                Product.query.filter_by(id=item.product_id).with_for_update().first()
            )
            variant = None
            if item.variant_id is not None:
                variant = (
                    ProductVariant.query.filter_by(
                        id=item.variant_id, product_id=item.product_id
                    )
                    .with_for_update()
                    .first()
                )
                if not variant:
                    raise ValueError(
                        "A purchased variant is no longer available for inventory restoration."
                    )
                variant.stock = int(variant.stock or 0) + int(item.quantity)
            else:
                if not product:
                    raise ValueError(
                        "A purchased product is no longer available for inventory restoration."
                    )
                product.stock = int(product.stock or 0) + int(item.quantity)

            db.session.add(
                InventoryLog(
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    change=int(item.quantity),
                    reason="ORDER_CANCELLED",
                )
            )

        order.status = OrderStatus.CANCELLED
        order.cancellation_reason = str(reason or "Customer cancellation").strip()[
            :2000
        ]
        order.cancelled_at = datetime.utcnow()
        refund_required = bool(
            order.payment
            and order.payment.status == "SUCCESS"
            and order.payment.transaction_id
        )
        if refund_required:
            order.payment.status = "REFUND_PENDING"

        OrderEventService.add(
            order, "ORDER_CANCELLED", "Order cancelled", order.cancellation_reason
        )
        NotificationService.create(
            account_id=account_id,
            title="Order cancelled",
            message=f"Order #{order.id} has been cancelled. Any applicable payment refund is pending processing.",
            notification_type=NotificationType.ORDER,
            dedupe_key=f"order:{order.id}:cancelled:customer",
        )
        db.session.commit()

        try:
            ShiprocketService.cancel_order_shipments(order.id)
        except Exception:
            pass

        if refund_required:
            try:
                RazorpayService.refund_payment(
                    order.payment.transaction_id, order.payment.amount
                )
                order.payment.status = "REFUNDED"
                NotificationService.create(
                    account_id=account_id,
                    title="Refund initiated",
                    message=f"A refund for order #{order.id} has been initiated through Razorpay.",
                    notification_type=NotificationType.ORDER,
                    dedupe_key=f"order:{order.id}:refund:customer",
                )
                db.session.commit()
            except Exception as exc:
                order.payment.failure_message = str(exc)[:500]
                order.payment.status = "REFUND_PENDING"
                db.session.commit()

        for item in order.items:
            try:
                StockAlertService.notify_available(item.product_id, item.variant_id)
            except Exception:
                db.session.rollback()

        return OrderService._serialize_order(order)

    @staticmethod
    def _supplier_groups(supplier_id, status=None, search=None):
        query = (
            OrderItem.query.join(Order, Order.id == OrderItem.order_id)
            .join(Product, Product.id == OrderItem.product_id)
            .filter(Product.seller_id == supplier_id)
        )
        if status:
            query = query.filter(Order.status == OrderStatus(status))
        if search:
            term = str(search).strip()
            if term:
                query = query.filter(
                    (Product.name.ilike(f"%{term}%"))
                    | (
                        Order.id == int(term)
                        if term.isdigit()
                        else Product.name.ilike(f"%{term}%")
                    )
                )
        rows = (
            db.session.query(OrderItem, Order, Product)
            .join(Order, Order.id == OrderItem.order_id)
            .join(Product, Product.id == OrderItem.product_id)
            .filter(Product.seller_id == supplier_id)
        )
        if status:
            rows = rows.filter(Order.status == OrderStatus(status))
        if search:
            term = str(search).strip()
            if term:
                rows = rows.filter(
                    (Product.name.ilike(f"%{term}%"))
                    | (
                        Order.id == int(term)
                        if term.isdigit()
                        else Product.name.ilike(f"%{term}%")
                    )
                )

        rows = rows.order_by(Order.created_at.desc(), Order.id.desc()).all()
        grouped = {}
        order_map = {}
        for item, order, product in rows:
            order_map[order.id] = order
            grouped.setdefault(order.id, []).append(item)
        return [(order_map[order_id], items) for order_id, items in grouped.items()]

    @staticmethod
    def _serialize_supplier_order(
        order, supplier_id, include_events=True, image_map=None
    ):
        items = [
            item
            for item in order.items
            if item.product and item.product.seller_id == supplier_id
        ]
        if not items:
            return None
        image_map = image_map if image_map is not None else _item_image_map(items)
        supplier_total = sum(float(item.subtotal or 0) for item in items)
        supplier_units = sum(int(item.quantity or 0) for item in items)
        return {
            "id": order.id,
            "status": order.status.value,
            "supplier_total": round(supplier_total, 2),
            "items_count": len(items),
            "units": supplier_units,
            "customer": {
                "name": order.delivery_full_name or order.customer_name,
                "phone": order.delivery_phone,
            },
            "delivery": {
                "full_name": order.delivery_full_name,
                "phone": order.delivery_phone,
                "address_line_1": order.delivery_address_line_1,
                "address_line_2": order.delivery_address_line_2,
                "landmark": order.delivery_landmark,
                "city": order.delivery_city,
                "state": order.delivery_state,
                "postal_code": order.delivery_postal_code,
                "country": order.delivery_country,
            },
            "delivery_expectation": {
                "label": "Estimated delivery",
                "window": None,
            },
            "payment_status": order.payment.status if order.payment else "UNKNOWN",
            "created_at": order.created_at,
            "cancelled_at": order.cancelled_at,
            "cancellation_reason": order.cancellation_reason,
            "invoice": None,
            "delivery_assignment": (
                {
                    "pickup_status": order.delivery_assignment.pickup_status.value,
                    "pickup_time": order.delivery_assignment.pickup_time,
                    "delivery_status": order.delivery_assignment.delivery_status.value,
                    "delivery_time": order.delivery_assignment.delivery_time,
                    "agent_name": order.delivery_assignment.agent_name,
                    "agent_phone": order.delivery_assignment.agent_phone,
                    "notes": order.delivery_assignment.notes,
                }
                if getattr(order, "delivery_assignment", None)
                else None
            ),
            "shipments": ShiprocketService.get_supplier_shipments(order, supplier_id),
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product_name_snapshot
                    or (item.product.name if item.product else "Product"),
                    "variant_id": item.variant_id,
                    "variant_name": item.variant_name_snapshot
                    or (item.variant.name if item.variant else None),
                    "variant_value": item.variant_value_snapshot
                    or (item.variant.value if item.variant else None),
                    "quantity": int(item.quantity or 0),
                    "unit_price": float(item.unit_price or 0),
                    "subtotal": float(item.subtotal or 0),
                    "image": _item_image(item, image_map),
                    "sku": (
                        item.variant.sku
                        if item.variant
                        else (item.product.sku if item.product else None)
                    ),
                }
                for item in items
            ],
            "events": (
                [
                    OrderEventService.serialize(event)
                    for event in order.events.order_by("occurred_at", "id").all()
                ]
                if include_events and getattr(order, "events", None)
                else []
            ),
        }

    @staticmethod
    def get_supplier_orders(supplier_id, status=None, search=None, page=1, per_page=25):
        page = max(1, int(page or 1))
        per_page = min(max(1, int(per_page or 25)), 100)
        groups = OrderService._supplier_groups(
            supplier_id, status=status, search=search
        )
        total = len(groups)
        start = (page - 1) * per_page
        end = start + per_page
        page_groups = groups[start:end]
        image_map = _item_image_map(
            [item for _, group_items in page_groups for item in group_items]
        )
        items = []
        for order, group_items in page_groups:
            supplier_items = [
                item
                for item in group_items
                if item.product and item.product.seller_id == supplier_id
            ]
            previews = []
            seen_keys = set()
            for item in supplier_items:
                key = (item.product_id, item.variant_id or 0)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                previews.append(
                    {
                        "product_id": item.product_id,
                        "product_name": item.product_name_snapshot
                        or (item.product.name if item.product else "Product"),
                        "variant_value": item.variant_value_snapshot
                        or (item.variant.value if item.variant else None),
                        "image": _item_image(item, image_map),
                    }
                )
                if len(previews) >= 4:
                    break
            items.append(
                {
                    "id": order.id,
                    "customer": order.delivery_full_name or order.customer_name,
                    "status": order.status.value,
                    "total": round(
                        sum(float(i.subtotal or 0) for i in supplier_items),
                        2,
                    ),
                    "items": sum(int(i.quantity or 0) for i in group_items),
                    "product_previews": previews,
                    "created_at": order.created_at,
                }
            )
        return {
            "orders": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page if total else 0,
                "total": total,
            },
        }

    @staticmethod
    def get_supplier_order(supplier_id, order_id):
        order = Order.query.get(order_id)
        if not order:
            return None
        return OrderService._serialize_supplier_order(
            order,
            supplier_id,
            include_events=True,
            image_map=_item_image_map(order.items),
        )

    @staticmethod
    def update_supplier_status(supplier_id, order_id, status):
        order = Order.query.filter_by(id=order_id).with_for_update().first()
        if not order:
            raise ValueError("Order not found.")
        if not any(
            item.product and item.product.seller_id == supplier_id
            for item in order.items
        ):
            raise ValueError("Order not found.")
        try:
            new_status = OrderStatus(str(status).upper())
        except ValueError:
            raise ValueError("Invalid order status.")

        # A supplier can initiate fulfillment while the overall order is PAID or
        # already PROCESSING. The latter is important for multi-supplier orders: a
        # second supplier still needs to provision only their own shipment.
        if order.status not in {OrderStatus.PAID, OrderStatus.PROCESSING} or new_status != OrderStatus.PROCESSING:
            raise ValueError(
                f"Suppliers cannot change {order.status.value} orders to {new_status.value}."
            )

        was_already_processing = order.status == OrderStatus.PROCESSING
        order.status = OrderStatus.PROCESSING

        assignment = DeliveryAssignment.query.filter_by(order_id=order.id).first()
        if not assignment:
            db.session.add(DeliveryAssignment(order_id=order.id))

        if not was_already_processing:
            OrderEventService.add(
                order,
                "SUPPLIER_PROCESSING",
                "Supplier processing",
                f"Supplier started processing order #{order.id}.",
            )
        db.session.commit()

        # Shiprocket provisioning starts ONLY because this supplier explicitly
        # clicked Start Processing. This call is supplier-scoped and idempotent.
        try:
            ShiprocketService.ensure_supplier_shipment(
                order.id, supplier_id, propagate=True
            )
        except ShiprocketError as exc:
            current_app.logger.error(
                "Shiprocket provisioning failed after supplier Start Processing: order=%s supplier=%s code=%s status=%s message=%s",
                order.id, supplier_id, exc.code, exc.status_code, str(exc)[:500],
            )
            raise
        except Exception as exc:
            current_app.logger.exception(
                "Unexpected Shiprocket provisioning failure after supplier Start Processing: order=%s supplier=%s: %s",
                order.id, supplier_id, str(exc)[:500],
            )
            raise

        order = Order.query.get(order.id)
        if not was_already_processing:
            NotificationService.create(
                order.account_id,
                "Order processing",
                f"Order #{order.id} is being prepared for shipment.",
                NotificationType.ORDER,
                dedupe_key=f"order:{order.id}:customer:supplier-processing",
            )
            try:
                NotificationService.notify_logistics(
                    title="New order ready for logistics",
                    message=f"Order #{order.id} is ready for pickup assignment.",
                    dedupe_key_prefix=f"order:{order.id}:logistics:ready",
                )
                db.session.commit()
            except Exception:
                db.session.rollback()

        return order

    @staticmethod
    def import_supplier_status_csv(supplier_id, file_bytes, filename):
        if not str(filename or "").lower().endswith(".csv"):
            raise ValueError("Only CSV files are accepted.")
        if len(file_bytes) > 2 * 1024 * 1024:
            raise ValueError("CSV must be 2 MB or smaller.")
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("CSV must be UTF-8 encoded.")

        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []
        headers = [str(value or "").strip().lower() for value in fieldnames]
        expected = ["order id", "status"]
        if headers != expected:
            raise ValueError("CSV columns must be exactly: Order ID, Status.")
        field_by_name = {str(name).strip().lower(): name for name in fieldnames}

        rows = []
        seen = set()
        for row_number, raw in enumerate(reader, start=2):
            order_id_text = str(raw.get(field_by_name["order id"]) or "").strip()
            status = str(raw.get(field_by_name["status"]) or "").strip().upper()
            if not order_id_text and not status:
                continue
            try:
                order_id = int(order_id_text)
            except (TypeError, ValueError):
                raise ValueError(f"Row {row_number}: Order ID must be a whole number.")
            if order_id in seen:
                raise ValueError(f"Row {row_number}: duplicate Order ID {order_id}.")
            seen.add(order_id)
            if status != OrderStatus.PROCESSING.value:
                raise ValueError(
                    f"Row {row_number}: supplier imports may only set status to PROCESSING."
                )
            rows.append((row_number, order_id, status))

        if not rows:
            raise ValueError("The CSV contains no order rows.")
        if len(rows) > 500:
            raise ValueError("CSV may contain at most 500 orders per import.")

        changed = []
        unchanged = []
        try:
            for row_number, order_id, status in rows:
                order = Order.query.filter_by(id=order_id).with_for_update().first()
                if not order or not any(
                    item.product and item.product.seller_id == supplier_id
                    for item in order.items
                ):
                    raise ValueError(
                        f"Row {row_number}: Order #{order_id} was not found for this supplier."
                    )
                if order.status == OrderStatus.PROCESSING:
                    unchanged.append(order_id)
                    continue
                if order.status != OrderStatus.PAID:
                    raise ValueError(
                        f"Row {row_number}: Order #{order_id} is {order.status.value} and cannot be moved to PROCESSING."
                    )

                order.status = OrderStatus.PROCESSING
                assignment = DeliveryAssignment.query.filter_by(
                    order_id=order.id
                ).first()
                if not assignment:
                    db.session.add(DeliveryAssignment(order_id=order.id))
                OrderEventService.add(
                    order,
                    "SUPPLIER_PROCESSING",
                    "Supplier processing",
                    f"Supplier started processing order #{order.id}.",
                )
                changed.append(order)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        for order in changed:
            try:
                ShiprocketService.ensure_supplier_shipment(
                    order.id, supplier_id, propagate=True
                )
            except Exception as exc:
                current_app.logger.exception(
                    "Shiprocket provisioning failed after supplier CSV processing: order=%s supplier=%s: %s",
                    order.id, supplier_id, str(exc)[:500],
                )
        for order in changed:
            NotificationService.create(
                order.account_id,
                "Order processing",
                f"Order #{order.id} is being prepared for shipment.",
                NotificationType.ORDER,
                dedupe_key=f"order:{order.id}:customer:supplier-processing",
            )
            try:
                NotificationService.notify_logistics(
                    title="New order ready for logistics",
                    message=f"Order #{order.id} is ready for pickup assignment.",
                    dedupe_key_prefix=f"order:{order.id}:logistics:ready",
                )
                db.session.commit()
            except Exception:
                db.session.rollback()

        return {
            "updated": len(changed),
            "unchanged": len(unchanged),
            "order_ids": [order.id for order in changed],
        }

    @staticmethod
    def get_supplier_earnings(supplier_id):
        groups = OrderService._supplier_groups(supplier_id)
        total_sales = delivered_sales = pending_sales = 0.0
        delivered_orders = units_sold = 0
        monthly_sales = {
            m: 0.0
            for m in (
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            )
        }
        product_sales = {}
        for order, supplier_items in groups:
            value = sum(float(i.subtotal or 0) for i in supplier_items)
            if order.status.value not in EXCLUDED_REVENUE:
                total_sales += value
            if order.status == OrderStatus.DELIVERED:
                delivered_sales += value
                delivered_orders += 1
                units_sold += sum(int(i.quantity or 0) for i in supplier_items)
                monthly_sales[order.created_at.strftime("%b")] += value
                for item in supplier_items:
                    product_sales[item.product.name] = product_sales.get(
                        item.product.name, 0
                    ) + float(item.subtotal or 0)
            elif order.status.value not in EXCLUDED_REVENUE:
                pending_sales += value
        return {
            "total_sales": round(total_sales, 2),
            "delivered_sales": round(delivered_sales, 2),
            "pending_sales": round(pending_sales, 2),
            "delivered_orders": delivered_orders,
            "units_sold": units_sold,
            "monthly_sales": {k: round(v, 2) for k, v in monthly_sales.items()},
            "top_products": sorted(
                [{"name": k, "revenue": round(v, 2)} for k, v in product_sales.items()],
                key=lambda x: x["revenue"],
                reverse=True,
            )[:10],
        }
