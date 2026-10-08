from datetime import datetime
from decimal import Decimal

from flask import current_app
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.core.business_rules import calculate_platform_charges, money
from app.extensions import db
from app.modules.accounts.models import Account
from app.modules.cart.models import CartItem
from app.modules.coupons.enums import DiscountType
from app.modules.coupons.models import Coupon
from app.modules.coupons.services import CouponService
from app.modules.customer_addresses.models import CustomerAddress
from app.modules.inventory.models import InventoryLog
from app.modules.invoices.models import Invoice
from app.modules.order_events.services import OrderEventService
from app.modules.order_items.models import OrderItem
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.modules.payments.models import Payment
from app.modules.products.models import Product
from app.modules.product_variants.models import ProductVariant
from app.modules.supplier_orders.models import DeliveryAssignment
from app.modules.stock_alerts.services import StockAlertService
from app.services.invoice_service import InvoiceService
from app.services.razorpay_service import RazorpayService
from app.modules.notifications.enums import NotificationType
from app.modules.notifications.services import NotificationService
from app.modules.admin.services import AdminNotificationService
from app.modules.shiprocket.service import ShiprocketError, ShiprocketService

from .models import CheckoutSession
from .repository import CheckoutRepository


class CheckoutService:
    @staticmethod
    def create_or_get(account_id):
        session = CheckoutRepository.get_active_by_account(account_id)
        if session:
            return session

        session = CheckoutSession(
            account_id=account_id,
            idempotency_key=uuid4().hex,
            payment_status="PENDING",
        )
        try:
            return CheckoutRepository.create(session)
        except IntegrityError:
            db.session.rollback()
            session = CheckoutRepository.get_active_by_account(account_id)
            if session:
                return session
            raise

    @staticmethod
    def _session(account_id, lock=False, create=True):
        session = CheckoutRepository.get_active_by_account(account_id, lock=lock)
        if not session and create:
            session = CheckoutService.create_or_get(account_id)
            if lock:
                session = CheckoutRepository.get_by_id(
                    account_id, session.id, lock=True
                )
        return session

    @staticmethod
    def _cart_snapshot(account_id):
        items = (
            CartItem.query.options(
                joinedload(CartItem.product).selectinload(Product.images),
                joinedload(CartItem.variant),
            )
            .filter_by(account_id=account_id)
            .order_by(CartItem.id.asc())
            .all()
        )
        if not items:
            raise ValueError("Cart is empty.")

        result = []
        subtotal = Decimal("0.00")
        total_items = 0
        issues = []

        for item in items:
            product = item.product
            variant = item.variant
            quantity = int(item.quantity or 0)

            if not product:
                issues.append(
                    {
                        "cart_item_id": item.id,
                        "message": "Product is no longer available.",
                    }
                )
                continue
            if quantity <= 0:
                issues.append(
                    {"cart_item_id": item.id, "message": "Cart quantity is invalid."}
                )
                continue
            if product.status != "ACTIVE":
                issues.append(
                    {
                        "cart_item_id": item.id,
                        "product_id": product.id,
                        "message": "Product is unavailable.",
                    }
                )
                continue
            if item.variant_id is not None and (
                not variant
                or variant.product_id != product.id
                or not getattr(variant, "is_active", True)
            ):
                issues.append(
                    {
                        "cart_item_id": item.id,
                        "product_id": product.id,
                        "message": "Selected variant is unavailable.",
                    }
                )
                continue

            unit_price = money(variant.price if variant else product.price)
            stock = int(variant.stock if variant else (product.stock or 0))
            item_subtotal = money(unit_price * quantity)
            subtotal += item_subtotal
            total_items += quantity

            if stock < quantity:
                issues.append(
                    {
                        "cart_item_id": item.id,
                        "product_id": product.id,
                        "variant_id": item.variant_id,
                        "message": f"Only {stock} unit{'s' if stock != 1 else ''} available.",
                    }
                )

            result.append(
                {
                    "cart_item_id": item.id,
                    "product_id": product.id,
                    "name": product.name,
                    "variant_id": item.variant_id,
                    "variant_name": variant.name if variant else None,
                    "variant_value": variant.value if variant else None,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "item_subtotal": item_subtotal,
                    "available_stock": stock,
                    "available": stock >= quantity
                    and product.status == "ACTIVE"
                    and (
                        item.variant_id is None
                        or (variant is not None and getattr(variant, "is_active", True))
                    ),
                    "image": product.images[0].image_url if product.images else None,
                }
            )

        return result, subtotal, total_items, issues

    @staticmethod
    def _coupon_and_discount(session, subtotal, items):
        if not session.coupon_id:
            return None, Decimal("0.00")

        coupon = Coupon.query.filter_by(id=session.coupon_id).first()
        coupon = CouponService.validate(
            coupon.code if coupon else "", subtotal, coupon=coupon
        )

        eligible_subtotal = subtotal
        if coupon.seller_id:
            cart_rows = (
                CartItem.query.options(joinedload(CartItem.product))
                .filter(CartItem.id.in_([row["cart_item_id"] for row in items]))
                .all()
            )
            seller_by_cart_item = {
                row.id: row.product.seller_id for row in cart_rows if row.product
            }
            eligible_subtotal = sum(
                (
                    row["item_subtotal"]
                    for row in items
                    if seller_by_cart_item.get(row["cart_item_id"]) == coupon.seller_id
                ),
                Decimal("0.00"),
            )
            if eligible_subtotal <= 0:
                raise ValueError("Coupon is not valid for the items in this cart.")

        return coupon, CouponService.calculate_discount(coupon, eligible_subtotal)

    @staticmethod
    def _calculate(session, persist=True):
        items, subtotal, total_items, issues = CheckoutService._cart_snapshot(
            session.account_id
        )
        coupon, discount = CheckoutService._coupon_and_discount(
            session, subtotal, items
        )
        taxable_base = money(max(subtotal - discount, Decimal("0.00")))
        charges = calculate_platform_charges(taxable_base)
        marketing_fee = money(charges["marketing_fee"])
        tax = money(charges["tax"])

        shipping_charge = Decimal("0.00")
        shipping_quote = None
        shipping_error = None
        if session.address_id and not issues:
            address = CustomerAddress.query.filter_by(
                id=session.address_id, account_id=session.account_id
            ).first()
            try:
                quote = ShiprocketService.quote_checkout_shipping(
                    session.account_id, address
                )
                shipping_charge = money(quote.get("shipping_charge") or 0)
                shipping_quote = quote
            except ShiprocketError as exc:
                shipping_error = str(exc)

        total = money(taxable_base + marketing_fee + tax + shipping_charge)

        if persist:
            session.subtotal = money(subtotal)
            session.discount = money(discount)
            session.taxable_base = taxable_base
            session.marketing_fee = marketing_fee
            session.tax = tax
            session.shipping_charge = shipping_charge
            session.shipping_quote = shipping_quote
            session.total = total
            db.session.flush()

        # Delivery estimates are owned by Shiprocket after a shipment exists.
        # Before supplier processing there is intentionally no courier ETA to report.
        estimate = {
            "label": "Estimated delivery",
            "window": None,
            "from": None,
            "to": None,
        }
        return {
            "checkout_session_id": session.id,
            "items": items,
            "total_items": total_items,
            "subtotal": money(subtotal),
            "discount": money(discount),
            "taxable_base": taxable_base,
            "marketing_fee": marketing_fee,
            "tax": tax,
            "shipping_charge": float(shipping_charge),
            "shipping_quote": shipping_quote,
            "shipping_error": shipping_error,
            "total": total,
            "coupon": ({"id": coupon.id, "code": coupon.code} if coupon else None),
            "issues": issues,
            "can_pay": bool(items and not issues and session.address_id and not shipping_error),
            "address_id": session.address_id,
            "payment_status": session.payment_status,
            "estimated_delivery": estimate,
            "razorpay_key_id": __import__("flask").current_app.config.get(
                "RAZORPAY_KEY_ID", ""
            ),
        }

    @staticmethod
    def get_session(account_id):
        session = CheckoutService._session(account_id)
        return CheckoutService._calculate(session)

    @staticmethod
    def validate_checkout(account_id):
        session = CheckoutService._session(account_id)
        return CheckoutService._calculate(session)

    @staticmethod
    def set_address(account_id, address_id):
        session = CheckoutService._session(account_id)
        if session.payment_status == "PAID":
            raise ValueError("Payment has already been verified for this checkout.")
        try:
            address_id = int(address_id)
        except (TypeError, ValueError):
            raise ValueError("Invalid delivery address.")
        address = CustomerAddress.query.filter_by(
            id=address_id, account_id=account_id
        ).first()
        if not address:
            raise ValueError("Address not found.")
        session.address_id = address.id
        session.razorpay_order_id = None
        session.payment_status = "PENDING"
        session.payment_error = None
        db.session.commit()
        return CheckoutService.get_session(account_id)

    @staticmethod
    def apply_coupon(account_id, code):
        session = CheckoutService._session(account_id)
        if session.payment_status == "PAID":
            raise ValueError("Payment has already been verified for this checkout.")
        code = str(code or "").strip().upper()
        if not code:
            session.coupon_id = None
            session.razorpay_order_id = None
            session.payment_status = "PENDING"
            session.payment_error = None
            db.session.commit()
            return CheckoutService.get_session(account_id)

        _, subtotal, _, _ = CheckoutService._cart_snapshot(account_id)
        coupon = Coupon.query.filter_by(code=code, is_active=True).first()
        CouponService.validate(code, subtotal, coupon=coupon)
        session.coupon_id = coupon.id
        session.razorpay_order_id = None
        session.payment_status = "PENDING"
        session.payment_error = None
        db.session.commit()
        return CheckoutService.get_session(account_id)

    @staticmethod
    def create_razorpay_order(account_id):
        session = CheckoutService._session(account_id, lock=True)
        if session.payment_status == "COMPLETED" and session.order_id:
            return {
                "order_id": session.razorpay_order_id,
                "amount": int(money(session.total) * 100),
                "currency": "INR",
                "order_created": True,
            }
        if not session.address_id:
            raise ValueError("Delivery address is required before payment.")
        previous_total = money(session.total or 0)
        existing_razorpay_order_id = session.razorpay_order_id
        summary = CheckoutService._calculate(session, persist=True)
        if summary.get("shipping_error"):
            raise ValueError(
                f"Delivery charge could not be calculated: {summary['shipping_error']}"
            )
        if summary["issues"]:
            raise ValueError(
                "Please resolve unavailable or out-of-stock items before payment."
            )
        if summary["total"] <= 0:
            raise ValueError("Invalid order amount.")

        if (
            existing_razorpay_order_id
            and session.payment_status == "PAYMENT_PENDING"
            and previous_total == summary["total"]
        ):
            return {
                "razorpay_order_id": existing_razorpay_order_id,
                "amount": int(summary["total"] * 100),
                "currency": "INR",
                "public_key": summary["razorpay_key_id"],
            }
        if existing_razorpay_order_id and session.payment_status == "PAYMENT_PENDING":
            # The locked checkout amount changed (for example, because Shiprocket
            # returned a different shipping quote). Never reuse a mismatched Razorpay order.
            session.razorpay_order_id = None
            session.payment_status = "PENDING"
            db.session.flush()

        try:
            gateway_order = RazorpayService.create_order(
                amount=summary["total"],
                receipt=f"clipcart_{account_id}_{session.id}",
            )
        except Exception as exc:
            session.payment_error = "Unable to initialize payment."
            db.session.commit()
            raise RuntimeError(str(exc))

        session.razorpay_order_id = gateway_order["id"]
        session.payment_status = "PAYMENT_PENDING"
        session.payment_error = None
        db.session.commit()

        return {
            "razorpay_order_id": gateway_order["id"],
            "amount": gateway_order["amount"],
            "currency": gateway_order.get("currency", "INR"),
            "public_key": summary["razorpay_key_id"],
        }

    @staticmethod
    def _lock_cart(account_id):
        items = (
            CartItem.query.filter_by(account_id=account_id)
            .order_by(CartItem.id.asc())
            .with_for_update()
            .all()
        )
        if not items:
            raise ValueError("Cart is empty.")
        return items

    @staticmethod
    def _finalize_paid_session(session):
        if session.order_id:
            return Order.query.get(session.order_id)

        account = Account.query.get(session.account_id)
        if not account:
            raise ValueError("Customer account not found.")
        if not session.address_id:
            raise ValueError("Delivery address is required.")
        address = CustomerAddress.query.filter_by(
            id=session.address_id, account_id=session.account_id
        ).first()
        if not address:
            raise ValueError("Delivery address is no longer available.")

        cart_items = CheckoutService._lock_cart(session.account_id)
        locked_rows = []
        subtotal = Decimal("0.00")

        for cart_item in cart_items:
            product = (
                Product.query.filter_by(id=cart_item.product_id)
                .with_for_update()
                .first()
            )
            if not product or product.status != "ACTIVE":
                raise ValueError("A cart item is no longer available.")
            variant = None
            if cart_item.variant_id is not None:
                variant = (
                    ProductVariant.query.filter_by(
                        id=cart_item.variant_id,
                        product_id=product.id,
                    )
                    .with_for_update()
                    .first()
                )
                if not variant or not getattr(variant, "is_active", True):
                    raise ValueError("A selected variant is no longer available.")

            stock = int(variant.stock if variant else (product.stock or 0))
            quantity = int(cart_item.quantity or 0)
            if quantity <= 0 or stock < quantity:
                raise ValueError(f"Insufficient stock for {product.name}.")

            unit_price = money(variant.price if variant else product.price)
            item_subtotal = money(unit_price * quantity)
            subtotal += item_subtotal
            locked_rows.append(
                (cart_item, product, variant, quantity, unit_price, item_subtotal)
            )

        coupon = None
        discount = Decimal("0.00")
        if session.coupon_id:
            coupon = (
                Coupon.query.filter_by(id=session.coupon_id).with_for_update().first()
            )
            CouponService.validate(
                coupon.code if coupon else "", subtotal, coupon=coupon
            )
            eligible = subtotal
            if coupon.seller_id:
                eligible = sum(
                    (
                        row[5]
                        for row in locked_rows
                        if row[1].seller_id == coupon.seller_id
                    ),
                    Decimal("0.00"),
                )
                if eligible <= 0:
                    raise ValueError("Coupon is not valid for the items in this cart.")
            discount = CouponService.calculate_discount(coupon, eligible)

        taxable_base = money(max(subtotal - discount, Decimal("0.00")))
        charges = calculate_platform_charges(taxable_base)
        marketing_fee = money(charges["marketing_fee"])
        tax = money(charges["tax"])
        shipping_charge = money(session.shipping_charge or 0)
        if shipping_charge < 0:
            raise ValueError("Invalid delivery charge.")
        total = money(taxable_base + marketing_fee + tax + shipping_charge)

        if money(session.total) != total:
            raise ValueError("Checkout amount changed. Please restart payment.")

        payment = (
            Payment.query.filter_by(checkout_session_id=session.id)
            .with_for_update()
            .first()
        )
        if payment and payment.status == "SUCCESS":
            if payment.orders:
                return payment.orders[0]
        if not payment:
            payment = Payment(
                account_id=session.account_id,
                checkout_session_id=session.id,
                gateway_order_id=session.razorpay_order_id,
                amount=total,
                payment_type="ONLINE",
                gateway="RAZORPAY",
                transaction_id=session.razorpay_payment_id,
                status="SUCCESS",
            )
            db.session.add(payment)
            db.session.flush()
        else:
            payment.amount = total
            payment.gateway_order_id = session.razorpay_order_id
            payment.transaction_id = session.razorpay_payment_id
            payment.status = "SUCCESS"
            payment.failure_message = None
            db.session.flush()

        order = Order(
            account_id=session.account_id,
            address_id=address.id,
            payment_id=payment.id,
            coupon_id=coupon.id if coupon else None,
            subtotal=subtotal,
            discount=discount,
            taxable_base=taxable_base,
            marketing_fee=marketing_fee,
            tax=tax,
            shipping_charge=shipping_charge,
            shipping_quote=session.shipping_quote,
            total=total,
            customer_name=account.full_name,
            customer_email=account.email,
            delivery_full_name=address.full_name,
            delivery_phone=address.phone,
            delivery_address_line_1=address.address_line_1,
            delivery_address_line_2=address.address_line_2,
            delivery_landmark=address.landmark,
            delivery_city=address.city,
            delivery_state=address.state,
            delivery_postal_code=address.postal_code,
            delivery_country=address.country,
            delivery_latitude=address.latitude,
            delivery_longitude=address.longitude,
            status=OrderStatus.PAID,
        )
        db.session.add(order)
        db.session.flush()

        for (
            cart_item,
            product,
            variant,
            quantity,
            unit_price,
            item_subtotal,
        ) in locked_rows:
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                variant_id=variant.id if variant else None,
                supplier_id_snapshot=product.seller_id,
                sku_snapshot=(variant.sku if variant else product.sku),
                shipping_weight_kg_snapshot=product.shipping_weight_kg,
                shipping_length_cm_snapshot=product.shipping_length_cm,
                shipping_width_cm_snapshot=product.shipping_width_cm,
                shipping_height_cm_snapshot=product.shipping_height_cm,
                product_name_snapshot=product.name,
                variant_name_snapshot=variant.name if variant else None,
                variant_value_snapshot=variant.value if variant else None,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=item_subtotal,
            )
            db.session.add(order_item)
            if variant:
                variant.stock -= quantity
                new_stock = int(variant.stock or 0)
                if new_stock <= int(product.low_stock_threshold or 5):
                    NotificationService.create(
                        account_id=product.seller_id,
                        title="Low stock alert" if new_stock > 0 else "Out of stock",
                        message=f"{product.name} ({variant.value}) has {new_stock} units remaining.",
                        notification_type=NotificationType.SYSTEM,
                        dedupe_key=f"supplier-stock:{product.seller_id}:{product.id}:{variant.id}:{new_stock}",
                        commit=False,
                    )
            else:
                product.stock = int(product.stock or 0) - quantity

            db.session.add(
                InventoryLog(
                    product_id=product.id,
                    variant_id=variant.id if variant else None,
                    change=-quantity,
                    reason="ORDER_PLACED",
                )
            )
            db.session.delete(cart_item)

        if coupon:
            coupon.used_count = int(coupon.used_count or 0) + 1

        CheckoutSession.query.filter_by(
            account_id=session.account_id,
            payment_status="PAYMENT_PENDING",
            order_id=None,
        ).update(
            {"payment_status": "CANCELLED"},
            synchronize_session=False,
        )
        session.payment_status = "COMPLETED"
        session.order_id = order.id

        db.session.add(
            Invoice(
                order_id=order.id,
                invoice_number=f"CC-INV-{order.id:08d}",
                status="PENDING",
            )
        )
        db.session.flush()

        OrderEventService.add(
            order,
            "ORDER_PLACED",
            "Order placed",
            f"Order #{order.id} was placed successfully.",
        )
        OrderEventService.add(
            order,
            "PAYMENT_CONFIRMED",
            "Payment confirmed",
            "Your Razorpay payment was verified successfully.",
        )
        OrderEventService.add(
            order,
            "AWAITING_SUPPLIER_PROCESSING",
            "Awaiting supplier processing",
            "The paid order is waiting for the supplier to start processing.",
        )

        assignment = DeliveryAssignment.query.filter_by(order_id=order.id).first()
        if not assignment:
            db.session.add(DeliveryAssignment(order_id=order.id))

        NotificationService.create(
            account_id=order.account_id,
            title="Order placed",
            message=f"Your order #{order.id} has been placed successfully.",
            notification_type=NotificationType.ORDER,
            dedupe_key=f"order:{order.id}:customer",
            commit=False,
        )

        supplier_ids = {
            product.seller_id
            for _, product, _, _, _, _ in locked_rows
            if product.seller_id
        }
        for supplier_id in supplier_ids:
            NotificationService.create(
                account_id=supplier_id,
                title="New customer order",
                message=f"Order #{order.id} contains products from your store.",
                notification_type=NotificationType.ORDER,
                dedupe_key=f"order:{order.id}:supplier:{supplier_id}",
                commit=False,
            )

        AdminNotificationService.notify(
            "New Order Received",
            f"Order #{order.id} was placed by {account.full_name} for ₹{float(order.total):,.2f}.",
            "ORDER",
            dedupe_key=f"order:{order.id}:admin",
            commit=False,
        )

        db.session.commit()

        try:
            InvoiceService.generate(order)
        except Exception:
            pass

        return order

    @staticmethod
    def payment_failed(account_id, data):
        session = CheckoutRepository.get_active_by_account(account_id, lock=True)
        if not session:
            raise ValueError("Checkout session not found.")

        error_data = data.get("error") if isinstance(data.get("error"), dict) else data
        metadata = error_data.get("metadata") if isinstance(error_data, dict) else None
        gateway_order_id = str(
            (metadata or {}).get("order_id") or data.get("razorpay_order_id") or ""
        ).strip()
        if gateway_order_id and gateway_order_id != session.razorpay_order_id:
            raise ValueError("Razorpay order does not match checkout.")

        description = str(
            (error_data or {}).get("description")
            or (error_data or {}).get("reason")
            or "Payment was not completed."
        ).strip()[:500]
        session.payment_status = (
            "PAYMENT_PENDING" if session.razorpay_order_id else "PENDING"
        )
        session.payment_error = description
        session.razorpay_payment_id = None
        session.razorpay_signature = None
        db.session.commit()
        return {"payment_status": session.payment_status, "message": description}

    @staticmethod
    def verify_payment(account_id, data):
        session = CheckoutRepository.get_active_by_account(account_id, lock=True)
        if not session:
            completed = (
                CheckoutSession.query.filter_by(
                    account_id=account_id, payment_status="COMPLETED"
                )
                .order_by(CheckoutSession.updated_at.desc())
                .first()
            )
            if completed and completed.order_id:
                return {"order_id": completed.order_id, "payment_status": "COMPLETED"}
            raise ValueError("Checkout session not found.")

        razorpay_order_id = str(data.get("razorpay_order_id") or "").strip()
        razorpay_payment_id = str(data.get("razorpay_payment_id") or "").strip()
        razorpay_signature = str(data.get("razorpay_signature") or "").strip()
        if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
            raise ValueError("Incomplete payment verification response.")
        if razorpay_order_id != session.razorpay_order_id:
            raise ValueError("Razorpay order does not match checkout.")

        existing_payment = (
            Payment.query.filter_by(transaction_id=razorpay_payment_id)
            .with_for_update()
            .first()
        )
        if existing_payment and existing_payment.status == "SUCCESS":
            if existing_payment.checkout_session_id != session.id:
                raise ValueError("Payment is already associated with another checkout.")
            session.razorpay_payment_id = razorpay_payment_id
            session.payment_status = "PAID"
            order = CheckoutService._finalize_paid_session(session)
            current_app.logger.info(
                "Verified payment finalized Clipcart order=%s; waiting for supplier Start Processing before Shiprocket provisioning.",
                order.id,
            )
            return {"order_id": order.id, "payment_status": "COMPLETED"}

        try:
            RazorpayService.verify_signature(
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
            )
            gateway_order = RazorpayService.get_order(razorpay_order_id)
            expected_paise = int(money(session.total) * Decimal("100"))
            actual_paise = int(gateway_order.get("amount", 0))
            if (
                actual_paise != expected_paise
                or gateway_order.get("currency", "INR") != "INR"
            ):
                raise ValueError("Razorpay order amount does not match checkout.")
            gateway_payment = RazorpayService.get_payment(razorpay_payment_id)
            if gateway_payment.get("order_id") != razorpay_order_id:
                raise ValueError("Razorpay payment does not belong to this checkout.")
            payment_amount = int(gateway_payment.get("amount", actual_paise))
            if payment_amount != expected_paise:
                raise ValueError("Razorpay payment amount does not match checkout.")
            if gateway_payment.get("status") != "captured":
                raise ValueError("Razorpay payment is not in a payable state.")
        except ValueError:
            session.payment_error = "Payment details did not match the checkout amount."
            session.payment_status = "PENDING"
            db.session.commit()
            raise
        except Exception:
            session.payment_error = "Unable to confirm Razorpay payment."
            session.payment_status = "PENDING"
            db.session.commit()
            raise ValueError("Unable to confirm Razorpay payment.")

        existing_gateway_payment = (
            Payment.query.filter_by(gateway_order_id=razorpay_order_id)
            .with_for_update()
            .first()
        )
        if (
            existing_gateway_payment
            and existing_gateway_payment.transaction_id
            not in (None, razorpay_payment_id)
        ):
            raise ValueError("This checkout already has a different payment.")

        session.razorpay_payment_id = razorpay_payment_id
        session.razorpay_signature = razorpay_signature
        session.payment_status = "PAID"
        session.payment_error = None
        try:
            order = CheckoutService._finalize_paid_session(session)
            current_app.logger.info(
                "Verified payment finalized Clipcart order=%s; waiting for supplier Start Processing before Shiprocket provisioning.",
                order.id,
            )
            return {"order_id": order.id, "payment_status": "COMPLETED"}
        except Exception as exc:
            captured_amount = Decimal(actual_paise) / Decimal("100")
            message = (
                str(exc)[:500]
                or "The order could not be created after payment verification."
            )
            return CheckoutService._recover_captured_payment(
                account_id=account_id,
                session_id=session.id,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                captured_amount=money(captured_amount),
                message=message,
            )

    @staticmethod
    def _recover_captured_payment(
        account_id,
        session_id,
        razorpay_order_id,
        razorpay_payment_id,
        captured_amount,
        message,
    ):
        # The gateway has captured funds but the order transaction failed. Never leave a customer
        # charged without an order: persist the payment as refund-pending and attempt a full refund.
        db.session.rollback()
        session = (
            CheckoutSession.query.filter_by(id=session_id, account_id=account_id)
            .with_for_update()
            .first()
        )
        if not session:
            raise RuntimeError(
                "Checkout session was lost while recovering a captured payment."
            )

        payment = (
            Payment.query.filter_by(checkout_session_id=session.id)
            .with_for_update()
            .first()
        )
        if not payment:
            payment = Payment(
                account_id=account_id,
                checkout_session_id=session.id,
                gateway_order_id=razorpay_order_id,
                amount=captured_amount,
                payment_type="ONLINE",
                gateway="RAZORPAY",
                transaction_id=razorpay_payment_id,
                status="REFUND_PENDING",
                failure_message=message,
            )
            db.session.add(payment)
        else:
            payment.gateway_order_id = razorpay_order_id
            payment.amount = captured_amount
            payment.transaction_id = razorpay_payment_id
            payment.status = "REFUND_PENDING"
            payment.failure_message = message

        session.payment_status = "REFUND_PENDING"
        session.payment_error = "Payment was received but the order could not be created; a refund is being processed."
        db.session.commit()

        try:
            RazorpayService.refund_payment(razorpay_payment_id, captured_amount)
            db.session.rollback()
            payment = Payment.query.filter_by(checkout_session_id=session.id).first()
            session = CheckoutSession.query.filter_by(
                id=session.id, account_id=account_id
            ).first()
            payment.status = "REFUNDED"
            payment.failure_message = message
            session.payment_status = "CANCELLED"
            session.payment_error = (
                "Payment was refunded because the order could not be created."
            )
            db.session.commit()
            NotificationService.create(
                account_id=account_id,
                title="Payment refunded",
                message="Your payment was verified but the order could not be created. The payment has been refunded.",
                notification_type=NotificationType.PAYMENT,
                dedupe_key=f"checkout:{session.id}:refunded",
            )
            return {
                "order_id": None,
                "payment_status": "REFUNDED",
                "message": "Payment was verified but the order could not be created. The payment has been refunded.",
            }
        except Exception:
            db.session.rollback()
            payment = Payment.query.filter_by(checkout_session_id=session.id).first()
            session = CheckoutSession.query.filter_by(
                id=session.id, account_id=account_id
            ).first()
            if payment:
                payment.status = "REFUND_PENDING"
                payment.failure_message = message
            if session:
                session.payment_status = "REFUND_PENDING"
                session.payment_error = "Payment was received, but the order could not be created. Refund is pending manual retry."
            db.session.commit()
            NotificationService.create(
                account_id=account_id,
                title="Refund pending",
                message="Your payment was received, but the order could not be created. A refund is being processed.",
                notification_type=NotificationType.PAYMENT,
                dedupe_key=f"checkout:{session_id}:refund-pending",
            )
            raise RuntimeError(
                "Payment was received but the order could not be created. Refund is pending."
            )

    @staticmethod
    def create_order(account_id):
        session = (
            CheckoutSession.query.filter_by(account_id=account_id)
            .order_by(CheckoutSession.updated_at.desc())
            .first()
        )
        if not session:
            raise ValueError("Checkout session not found.")
        if session.order_id:
            return Order.query.get(session.order_id)
        if session.payment_status != "PAID":
            raise ValueError("Payment not completed.")
        return CheckoutService._finalize_paid_session(session)
