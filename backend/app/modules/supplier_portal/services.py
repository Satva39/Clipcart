import re

from collections import defaultdict
from datetime import date, datetime, timedelta
from sqlalchemy import case, func
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.modules.inventory.models import InventoryLog
from app.modules.notifications.models import Notification
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.modules.order_items.models import OrderItem
from app.modules.payouts.models import SupplierPayout
from app.modules.product_variants.models import ProductVariant
from app.modules.products.models import Product
from app.modules.seller_verification.models import SellerVerification
from app.modules.payouts.models import SupplierPayoutAccount
from app.modules.accounts.models import Account

EXCLUDED_REVENUE = {OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value}
FINAL_STATUSES = {
    OrderStatus.DELIVERED.value,
    OrderStatus.CANCELLED.value,
    OrderStatus.RETURNED.value,
}


def _parse_date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Dates must use YYYY-MM-DD format.")


def resolve_range(start, end):
    today = date.today()
    start_date = _parse_date(start, today - timedelta(days=29))
    end_date = _parse_date(end, today)
    if start_date > end_date:
        raise ValueError("Start date cannot be after end date.")
    return start_date, end_date


def _supplier_item_query(supplier_id, start_date=None, end_date=None):
    query = (
        db.session.query(OrderItem, Order, Product)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(Product.seller_id == supplier_id)
    )
    if start_date:
        query = query.filter(func.date(Order.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(Order.created_at) <= end_date)
    return query


def _supplier_order_rows(supplier_id, start_date=None, end_date=None):
    rows = _supplier_item_query(supplier_id, start_date, end_date).all()
    grouped = {}
    for item, order, product in rows:
        grouped.setdefault(order.id, {"order": order, "items": []})["items"].append(
            item
        )
    return list(grouped.values())


def _supplier_revenue(items, order_status):
    if order_status in EXCLUDED_REVENUE:
        return 0.0
    return round(sum(float(item.subtotal or 0) for item in items), 2)


def _low_stock(product):
    threshold = int(product.low_stock_threshold or 5)
    if product.variants:
        active_variants = [v for v in product.variants if getattr(v, "is_active", True)]
        return any(int(v.stock or 0) <= threshold for v in active_variants), any(
            int(v.stock or 0) == 0 for v in active_variants
        )
    stock = int(product.stock or 0)
    return stock <= threshold, stock == 0


class SupplierPortalService:
    @staticmethod
    def _supplier_revenue(items, order_status):
        return _supplier_revenue(items, order_status)

    @staticmethod
    def profile(supplier_id):
        account = Account.query.filter_by(id=supplier_id).first()
        verification = SellerVerification.query.filter_by(
            account_id=supplier_id
        ).first()
        payout = SupplierPayoutAccount.query.filter_by(account_id=supplier_id).first()
        if not account or str(account.role.value) != "SUPPLIER":
            return None
        return {
            "account": {
                "id": account.id,
                "full_name": account.full_name,
                "email": account.email,
                "phone": account.phone,
                "status": account.status.value if account.status else None,
                "email_verified": bool(account.email_verified),
                "phone_verified": bool(account.phone_verified),
            },
            "business": {
                "business_name": verification.business_name if verification else None,
                "gst_number": verification.gst_number if verification else None,
                "verification_status": (
                    verification.status if verification else "PENDING"
                ),
                "registration_fee_paid": (
                    bool(verification.registration_fee_paid) if verification else False
                ),
                "payment_id": verification.payment_id if verification else None,
                "return_address": {
                    "address_line_1": (
                        verification.return_address_line_1 if verification else None
                    ),
                    "address_line_2": (
                        verification.return_address_line_2 if verification else None
                    ),
                    "landmark": verification.return_landmark if verification else None,
                    "city": verification.return_city if verification else None,
                    "state": verification.return_state if verification else None,
                    "postal_code": (
                        verification.return_postal_code if verification else None
                    ),
                    "country": verification.return_country if verification else "India",
                    "latitude": (float(verification.return_latitude) if verification and verification.return_latitude is not None else None),
                    "longitude": (float(verification.return_longitude) if verification and verification.return_longitude is not None else None),
                },
            },
            "payout": {
                "id": payout.id if payout else None,
                "holder_name": payout.holder_name if payout else account.full_name,
                "bank_name": payout.bank_name if payout else None,
                "account_number": (
                    ("••••••••" + payout.account_number[-4:])
                    if payout and payout.account_number
                    else None
                ),
                "ifsc": payout.ifsc if payout else None,
                "upi_id": payout.upi_id if payout else None,
                "is_verified": bool(payout.is_verified) if payout else False,
            },
        }

    @staticmethod
    def update_profile(supplier_id, data):
        account = Account.query.filter_by(id=supplier_id).first()
        if not account or str(account.role.value) != "SUPPLIER":
            raise ValueError("Supplier account not found.")

        full_name = str(data.get("full_name", account.full_name or "")).strip()
        phone = str(data.get("phone", account.phone or "")).strip()
        if len(full_name) < 3:
            raise ValueError("Full name must contain at least 3 characters.")
        account.full_name = full_name
        if phone:
            account.phone = phone

        verification = SellerVerification.query.filter_by(
            account_id=supplier_id
        ).first()
        if not verification:
            verification = SellerVerification(account_id=supplier_id)
            db.session.add(verification)
        verification.business_name = (
            str(data.get("business_name", verification.business_name or "")).strip()
            or None
        )
        verification.gst_number = (
            str(data.get("gst_number", verification.gst_number or "")).strip() or None
        )
        return_address = data.get("return_address") or {}
        address_fields = {
            "address_line_1", "address_line_2", "landmark", "city",
            "state", "postal_code", "country",
        }
        warehouse_address_changed = any(field in return_address for field in address_fields) and any(
            str(return_address.get(field, getattr(verification, {
                "address_line_1": "return_address_line_1",
                "address_line_2": "return_address_line_2",
                "landmark": "return_landmark",
                "city": "return_city",
                "state": "return_state",
                "postal_code": "return_postal_code",
                "country": "return_country",
            }[field], "")) or "").strip()
            != str(getattr(verification, {
                "address_line_1": "return_address_line_1",
                "address_line_2": "return_address_line_2",
                "landmark": "return_landmark",
                "city": "return_city",
                "state": "return_state",
                "postal_code": "return_postal_code",
                "country": "return_country",
            }[field], "") or "").strip()
            for field in address_fields
        )
        postal_code = re.sub(r"\s+", "", str(return_address.get("postal_code", verification.return_postal_code or "") or ""))
        country = str(return_address.get("country", verification.return_country or "India") or "India").strip() or "India"
        if country.casefold() == "india" and postal_code and not re.fullmatch(r"[1-9]\d{5}", postal_code):
            raise ValueError("Supplier Indian postal code must be a valid 6-digit pincode.")
        keep_existing_coordinates = not warehouse_address_changed and not ({"latitude", "longitude"} & return_address.keys())
        latitude = verification.return_latitude if keep_existing_coordinates else return_address.get("latitude")
        longitude = verification.return_longitude if keep_existing_coordinates else return_address.get("longitude")
        if latitude is not None:
            try:
                latitude = float(latitude)
            except (TypeError, ValueError):
                raise ValueError("Supplier latitude must be a valid number.")
            if not -90 <= latitude <= 90:
                raise ValueError("Supplier latitude must be between -90 and 90.")
        if longitude is not None:
            try:
                longitude = float(longitude)
            except (TypeError, ValueError):
                raise ValueError("Supplier longitude must be a valid number.")
            if not -180 <= longitude <= 180:
                raise ValueError("Supplier longitude must be between -180 and 180.")
        if (latitude is None) != (longitude is None):
            raise ValueError("Supplier latitude and longitude must be provided together.")
        verification.return_address_line_1 = (
            str(
                return_address.get(
                    "address_line_1", verification.return_address_line_1 or ""
                )
            ).strip()
            or None
        )
        verification.return_address_line_2 = (
            str(
                return_address.get(
                    "address_line_2", verification.return_address_line_2 or ""
                )
            ).strip()
            or None
        )
        verification.return_landmark = (
            str(
                return_address.get("landmark", verification.return_landmark or "")
            ).strip()
            or None
        )
        verification.return_city = (
            str(return_address.get("city", verification.return_city or "")).strip()
            or None
        )
        verification.return_state = (
            str(return_address.get("state", verification.return_state or "")).strip()
            or None
        )
        verification.return_postal_code = postal_code or None
        verification.return_country = country
        verification.return_latitude = latitude
        verification.return_longitude = longitude
        db.session.commit()
        return SupplierPortalService.profile(supplier_id)

    @staticmethod
    def dashboard(supplier_id, start=None, end=None):
        start_date, end_date = resolve_range(start, end)
        rows = _supplier_order_rows(supplier_id, start_date, end_date)
        products = (
            Product.query.options(selectinload(Product.variants))
            .filter_by(seller_id=supplier_id)
            .all()
        )
        payout_totals = (
            db.session.query(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                SupplierPayout.status.in_(["PENDING", "PROCESSING"]),
                                SupplierPayout.amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                SupplierPayout.status.in_(
                                    ["PENDING", "PROCESSING", "PAID"]
                                ),
                                SupplierPayout.amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .filter(SupplierPayout.account_id == supplier_id)
            .first()
        )
        payout_pending, allocated = payout_totals or (0, 0)

        order_count = len(rows)
        pending_orders = 0
        delivered_orders = 0
        cancelled = 0
        returned = 0
        gross_sales = 0.0
        delivered_revenue = 0.0
        units_sold = 0
        for group in rows:
            order = group["order"]
            status = order.status.value
            revenue = _supplier_revenue(group["items"], status)
            gross_sales += revenue
            if status == OrderStatus.DELIVERED.value:
                delivered_orders += 1
                delivered_revenue += revenue
                units_sold += sum(int(i.quantity or 0) for i in group["items"])
            elif status == OrderStatus.CANCELLED.value:
                cancelled += 1
            elif status == OrderStatus.RETURNED.value:
                returned += 1
            elif status not in FINAL_STATUSES:
                pending_orders += 1

        low_stock_products = 0
        out_of_stock_products = 0
        active_products = 0
        for product in products:
            if product.status == "ACTIVE":
                active_products += 1
            low, out = _low_stock(product)
            low_stock_products += int(low)
            out_of_stock_products += int(out)

        delivered_all_sales = (
            db.session.query(func.coalesce(func.sum(OrderItem.subtotal), 0))
            .join(Order, Order.id == OrderItem.order_id)
            .join(Product, Product.id == OrderItem.product_id)
            .filter(
                Product.seller_id == supplier_id,
                Order.status == OrderStatus.DELIVERED,
            )
            .scalar()
        )
        payout_available = max(
            0.0, float(delivered_all_sales or 0) - float(allocated or 0)
        )

        recent_orders = []
        for group in sorted(
            rows, key=lambda g: g["order"].created_at or datetime.min, reverse=True
        )[:8]:
            order = group["order"]
            recent_orders.append(
                {
                    "id": order.id,
                    "status": order.status.value,
                    "created_at": order.created_at,
                    "customer_name": order.customer_name,
                    "supplier_total": _supplier_revenue(
                        group["items"], order.status.value
                    ),
                    "items": sum(int(i.quantity or 0) for i in group["items"]),
                }
            )

        notifications = (
            Notification.query.filter_by(account_id=supplier_id)
            .order_by(Notification.created_at.desc())
            .limit(8)
            .all()
        )
        return {
            "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "metrics": {
                "total_sales": round(gross_sales, 2),
                "revenue": round(delivered_revenue, 2),
                "order_count": order_count,
                "pending_orders": pending_orders,
                "delivered_orders": delivered_orders,
                "cancelled_orders": cancelled,
                "returned_orders": returned,
                "units_sold": units_sold,
                "product_count": len(products),
                "active_product_count": active_products,
                "low_stock_count": low_stock_products,
                "out_of_stock_count": out_of_stock_products,
                "pending_payout": round(payout_pending, 2),
                "available_payout": round(payout_available, 2),
            },
            "recent_orders": recent_orders,
            "recent_notifications": [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "type": n.notification_type,
                    "is_read": n.is_read,
                    "created_at": n.created_at,
                }
                for n in notifications
            ],
        }

    @staticmethod
    def analytics(supplier_id, start=None, end=None):
        start_date, end_date = resolve_range(start, end)
        rows = _supplier_order_rows(supplier_id, start_date, end_date)
        products = (
            Product.query.options(selectinload(Product.variants))
            .filter_by(seller_id=supplier_id)
            .all()
        )
        product_map = {product.id: product for product in products}
        product_stats = defaultdict(
            lambda: {
                "revenue": 0.0,
                "units": 0,
                "orders": 0,
                "cancelled": 0,
                "returned": 0,
            }
        )
        daily = defaultdict(lambda: {"sales": 0.0, "orders": 0, "units": 0})
        status_counts = defaultdict(int)

        for group in rows:
            order = group["order"]
            status = order.status.value
            status_counts[status] += 1
            supplier_revenue = _supplier_revenue(group["items"], status)
            key = (
                order.created_at.date().isoformat()
                if order.created_at
                else start_date.isoformat()
            )
            daily[key]["orders"] += 1
            if status not in EXCLUDED_REVENUE:
                daily[key]["sales"] += supplier_revenue
            for item in group["items"]:
                product = product_map.get(item.product_id)
                if not product:
                    continue
                stats = product_stats[product.id]
                stats["orders"] += 1
                if status in EXCLUDED_REVENUE:
                    if status == OrderStatus.CANCELLED.value:
                        stats["cancelled"] += 1
                    if status == OrderStatus.RETURNED.value:
                        stats["returned"] += 1
                else:
                    stats["revenue"] += float(item.subtotal or 0)
                    stats["units"] += int(item.quantity or 0)
                    daily[key]["units"] += int(item.quantity or 0)

        ordered_days = []
        current = start_date
        while current <= end_date:
            bucket = daily[current.isoformat()]
            ordered_days.append(
                {
                    "date": current.isoformat(),
                    "sales": round(bucket["sales"], 2),
                    "orders": bucket["orders"],
                    "units": bucket["units"],
                }
            )
            current += timedelta(days=1)

        total_sales = sum(item["sales"] for item in ordered_days)
        total_orders = len(rows)
        units_sold = sum(item["units"] for item in ordered_days)
        aov = total_sales / total_orders if total_orders else 0
        cancelled = status_counts[OrderStatus.CANCELLED.value]
        returned = status_counts[OrderStatus.RETURNED.value]
        denominator = max(total_orders, 1)
        low_products = []
        for product in products:
            stats = product_stats[product.id]
            low, out = _low_stock(product)
            if stats["units"] == 0:
                low_products.append(
                    {
                        "id": product.id,
                        "name": product.name,
                        "units": 0,
                        "revenue": 0,
                        "stock": int(product.stock or 0),
                        "low_stock": low,
                        "out_of_stock": out,
                    }
                )

        top_products = sorted(
            [
                {
                    "id": pid,
                    "name": product_map[pid].name if pid in product_map else "Product",
                    **{
                        k: round(v, 2) if k == "revenue" else v
                        for k, v in stats.items()
                    },
                }
                for pid, stats in product_stats.items()
            ],
            key=lambda item: (item["revenue"], item["units"]),
            reverse=True,
        )[:10]
        low_candidates = {row["id"]: row for row in low_products}
        for pid, stats in product_stats.items():
            product = product_map.get(pid)
            if not product:
                continue
            low, out = _low_stock(product)
            low_candidates[pid] = {
                "id": pid,
                "name": product.name,
                "units": stats["units"],
                "revenue": round(stats["revenue"], 2),
                "stock": int(product.stock or 0),
                "low_stock": low,
                "out_of_stock": out,
            }
        low_performing = sorted(
            low_candidates.values(), key=lambda x: (x["units"], x["revenue"])
        )[:10]

        logs = (
            InventoryLog.query.join(Product, Product.id == InventoryLog.product_id)
            .filter(
                Product.seller_id == supplier_id,
                func.date(InventoryLog.created_at) >= start_date,
                func.date(InventoryLog.created_at) <= end_date,
            )
            .order_by(InventoryLog.created_at.desc())
            .limit(100)
            .all()
        )
        stock_movement = [
            {
                "id": log.id,
                "product_id": log.product_id,
                "variant_id": log.variant_id,
                "change": log.change,
                "reason": log.reason,
                "created_at": log.created_at,
                "product_name": log.product.name if log.product else "Product",
                "variant": (log.variant.value if log.variant else None),
            }
            for log in logs
        ]
        payouts = (
            SupplierPayout.query.filter_by(account_id=supplier_id)
            .order_by(SupplierPayout.created_at.desc())
            .limit(100)
            .all()
        )
        payout_history = [
            {
                "id": p.id,
                "amount": float(p.amount or 0),
                "status": p.status,
                "reference_id": p.reference_id,
                "created_at": p.created_at,
                "processed_at": p.processed_at,
            }
            for p in payouts
        ]
        return {
            "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "sales": round(total_sales, 2),
                "orders": total_orders,
                "units_sold": units_sold,
                "average_order_value": round(aov, 2),
                "cancellation_rate": round((cancelled / denominator) * 100, 2),
                "return_rate": round((returned / denominator) * 100, 2),
                "cancelled_orders": cancelled,
                "returned_orders": returned,
            },
            "series": ordered_days,
            "top_products": top_products,
            "low_performing_products": low_performing,
            "stock_movement": stock_movement,
            "payout_history": payout_history,
        }

    @staticmethod
    def catalog(supplier_id, search=None, status=None, page=1, per_page=20):
        page = max(int(page or 1), 1)
        per_page = min(max(int(per_page or 20), 1), 100)
        query = Product.query.options(
            selectinload(Product.category),
            selectinload(Product.brand),
            selectinload(Product.images),
            selectinload(Product.variants),
        ).filter_by(seller_id=supplier_id)
        if search:
            query = query.filter(Product.name.ilike(f"%{str(search).strip()}%"))
        if status:
            query = query.filter(Product.status == str(status).upper())
        pagination = query.order_by(Product.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return {
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "price": float(p.price or 0),
                    "compare_price": (
                        float(p.compare_price) if p.compare_price is not None else None
                    ),
                    "stock": int(p.stock or 0),
                    "status": p.status,
                    "category": p.category.name if p.category else None,
                    "brand": p.brand.name if p.brand else None,
                    "image": p.images[0].image_url if p.images else None,
                    "low_stock_threshold": int(p.low_stock_threshold or 5),
                    "variant_count": len(p.variants),
                    "active_variant_count": sum(
                        bool(getattr(v, "is_active", True)) for v in p.variants
                    ),
                }
                for p in pagination.items
            ],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages,
                "total": pagination.total,
            },
        }
