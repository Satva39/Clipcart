from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, current_app, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import func, or_

from app.core.jwt import portal_for_role
from app.core.security import verify_password, hash_password
from app.extensions import db
from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.models import Account
from app.modules.admin.authorization import admin_authorized, get_authorized_admin
from app.modules.admin.models import AdminAuditLog, AdminBanner, PlatformSetting
from app.modules.admin.services import (
    AdminAuditService,
    AdminBannerService,
    AdminNotificationService,
    AdminPasswordService,
    PlatformSettingsService,
)
from app.modules.brands.models import Brand
from app.modules.categories.models import Category
from app.modules.notifications.models import Notification
from app.modules.notifications.services import NotificationService
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.modules.payments.models import Payment
from app.modules.payouts.models import SupplierPayout, SupplierPayoutAccount
from app.modules.products.models import Product
from app.services.cloudinary_service import CloudinaryService
from app.modules.seller_verification.models import SellerVerification
from app.utils.response import error_response, success_response

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _admin_token_pair(account):
    claims = {
        "role": account.role.value,
        "email": account.email,
        "portal": portal_for_role(account.role.value),
    }
    return {
        "access_token": create_access_token(
            identity=str(account.id),
            additional_claims=claims,
            expires_delta=current_app.config["ADMIN_ACCESS_TOKEN_EXPIRES"],
        ),
        "refresh_token": create_refresh_token(
            identity=str(account.id),
            additional_claims=claims,
            expires_delta=current_app.config["ADMIN_REFRESH_TOKEN_EXPIRES"],
        ),
    }


def _account_payload(account):
    return {
        "id": account.id,
        "full_name": account.full_name,
        "email": account.email,
        "phone": account.phone,
        "status": account.status.value if account.status else None,
        "role": account.role.value if account.role else None,
        "email_verified": bool(account.email_verified),
        "phone_verified": bool(account.phone_verified),
        "created_at": account.created_at,
        "last_login": account.last_login,
    }


def _parse_date(raw, end=False):
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d") + (
                timedelta(days=1) if end else timedelta()
            )
        except ValueError:
            raise ValueError("Dates must use YYYY-MM-DD format.")
    return None


def _window():
    end = _parse_date(request.args.get("end_date"), end=True)
    start = _parse_date(request.args.get("start_date"))
    if end is None:
        end = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
    if start is None:
        start = end - timedelta(days=30)
    if start >= end:
        raise ValueError("start_date must be before end_date.")
    return start, end


def _growth(current, previous):
    current = float(current or 0)
    previous = float(previous or 0)
    if previous == 0:
        return None if current else 0.0
    return round((current - previous) / previous * 100, 2)


def _paginate(query, default=25):
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", default, type=int), 1), 100)
    return query.paginate(page=page, per_page=per_page, error_out=False)


def _pagination(p):
    return {
        "page": p.page,
        "pages": p.pages,
        "per_page": p.per_page,
        "total": p.total,
        "has_next": p.has_next,
        "has_prev": p.has_prev,
    }


def _coerce_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off", ""}:
        return False
    raise ValueError("Expected a boolean value.")


def _parse_banner_datetime(raw):
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    text = str(raw).strip()
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if value.tzinfo:
            value = value.astimezone(__import__("datetime").timezone.utc).replace(
                tzinfo=None
            )
        return value
    except ValueError:
        raise ValueError("Banner dates must be valid ISO dates/times.")


def _validate_product_input(data, product=None, admin_id=None):
    name = str(data.get("name", product.name if product else "")).strip()
    description = str(
        data.get("description", product.description if product else "")
    ).strip()
    sku = str(data.get("sku", product.sku if product else "")).strip()
    category_id = data.get("category_id", product.category_id if product else None)
    brand_id = data.get("brand_id", product.brand_id if product else None)

    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        raise ValueError("A valid category is required.")

    try:
        brand_id = int(brand_id) if brand_id not in (None, "") else None
        price = Decimal(str(data.get("price", product.price if product else 0)))
        stock = int(data.get("stock", product.stock if product else 0))
        threshold = int(
            data.get(
                "low_stock_threshold",
                product.low_stock_threshold if product else 5,
            )
        )
        raw_compare = data.get(
            "compare_price",
            product.compare_price if product else None,
        )
        compare_price = None if raw_compare in (None, "") else Decimal(str(raw_compare))
    except (TypeError, ValueError, ArithmeticError):
        raise ValueError("Price, stock or comparison values are invalid.")

    if len(name) < 2 or not description or not sku:
        raise ValueError("Name, description and SKU are required.")
    if price < 0 or stock < 0 or threshold < 0:
        raise ValueError("Price and stock cannot be negative.")
    if not Category.query.get(category_id):
        raise ValueError("Category does not exist.")
    if brand_id is not None and not Brand.query.get(brand_id):
        raise ValueError("Brand does not exist.")

    duplicate = Product.query.filter(Product.sku == sku)
    if product:
        duplicate = duplicate.filter(Product.id != product.id)
    if duplicate.first():
        raise ValueError("SKU already exists.")

    if compare_price is not None and compare_price < price:
        raise ValueError("Compare price cannot be lower than the selling price.")

    status = str(data.get("status", product.status if product else "ACTIVE")).upper()
    if status not in {"ACTIVE", "INACTIVE", "PENDING_REVIEW", "REJECTED"}:
        raise ValueError("Invalid moderation status.")

    return {
        "seller_id": admin_id,
        "category_id": category_id,
        "brand_id": brand_id,
        "name": name[:255],
        "description": description,
        "price": price,
        "compare_price": compare_price,
        "stock": stock,
        "low_stock_threshold": threshold,
        "sku": sku,
        "status": status,
        "is_featured": bool(
            data.get("is_featured", product.is_featured if product else False)
        ),
        "highlights": data.get("highlights", product.highlights if product else [])
        or [],
        "specifications": data.get(
            "specifications", product.specifications if product else {}
        )
        or {},
    }


@admin_bp.post("/auth/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    configured = current_app.config.get("CLIPCART_ADMIN_EMAIL", "")

    if not configured:
        return error_response("Admin identity is not configured.", 500)

    account = Account.query.filter(
        func.lower(Account.email) == configured,
        Account.role == UserRole.ADMIN,
        Account.status == UserStatus.ACTIVE,
    ).first()

    if (
        email != configured
        or not account
        or not verify_password(password, account.password_hash)
    ):
        return error_response("Invalid admin credentials.", 401)

    account.last_login = datetime.utcnow()
    db.session.commit()
    return success_response(
        "Admin login successful.",
        {"user": _account_payload(account), **_admin_token_pair(account)},
    )


@admin_bp.post("/auth/refresh")
@jwt_required(refresh=True)
def admin_refresh():
    admin = get_authorized_admin()
    if not admin:
        return error_response("Admin session is no longer valid.", 401)

    return success_response(
        "Admin access token refreshed.",
        {
            "access_token": create_access_token(
                identity=str(admin.id),
                additional_claims={
                    "role": "ADMIN",
                    "email": admin.email,
                    "portal": "admin",
                },
                expires_delta=current_app.config["ADMIN_ACCESS_TOKEN_EXPIRES"],
            )
        },
    )


@admin_bp.post("/auth/logout")
@admin_authorized
def admin_logout():
    from app.modules.auth.models import RevokedToken

    account_id = int(get_jwt_identity())
    tokens_to_revoke = [get_jwt()]

    data = request.get_json(silent=True) or {}
    refresh_token = str(data.get("refresh_token", "")).strip()
    if refresh_token:
        from flask_jwt_extended import decode_token

        try:
            refresh_claims = decode_token(
                refresh_token,
                allow_expired=False,
                csrf_value=None,
            )
            if (
                str(refresh_claims.get("role", "")).upper() == "ADMIN"
                and str(refresh_claims.get("portal", "")).lower() == "admin"
                and str(refresh_claims.get("sub")) == str(account_id)
            ):
                tokens_to_revoke.append(refresh_claims)
        except Exception:
            pass

    for token in tokens_to_revoke:
        jti = token.get("jti")
        if jti and not RevokedToken.query.filter_by(jti=jti).first():
            db.session.add(
                RevokedToken(
                    jti=jti,
                    account_id=account_id,
                    token_type=token.get("type", "access"),
                    expires_at=datetime.utcfromtimestamp(token["exp"]),
                )
            )
    db.session.commit()
    return success_response("Admin logged out.")


@admin_bp.post("/auth/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    generic = "If this email belongs to the Clipcart administrator, a password reset email has been sent."
    configured = current_app.config.get("CLIPCART_ADMIN_EMAIL", "")
    if not configured or email != configured:
        return success_response(generic)

    account = Account.query.filter(
        func.lower(Account.email) == configured,
        Account.role == UserRole.ADMIN,
        Account.status == UserStatus.ACTIVE,
    ).first()
    if not account:
        return success_response(generic)

    try:
        AdminPasswordService.send_reset_email(account)
    except RuntimeError:
        current_app.logger.error("Admin password reset email is not configured.")
        return error_response("Password reset service is temporarily unavailable.", 503)
    except Exception:
        current_app.logger.exception("Admin password reset email delivery failed.")
        return error_response("Password reset service is temporarily unavailable.", 503)

    return success_response(generic)


@admin_bp.post("/auth/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = str(data.get("token", "")).strip()
    password = str(data.get("password", ""))
    confirm = str(data.get("confirm_password", password))

    if not token:
        return error_response("Reset token is required.", 400)

    try:
        account = AdminPasswordService.verify_reset_token(token)
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters.")
        if password != confirm:
            raise ValueError("Passwords do not match.")
        account.password_hash = hash_password(password)
        AdminAuditService.record(
            account.id,
            "PASSWORD_RESET",
            "ADMIN_ACCOUNT",
            account.id,
            commit=False,
        )
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc), 400)

    return success_response("Admin password reset successfully.")


@admin_bp.get("/profile")
@admin_authorized
def profile():
    admin = get_authorized_admin()
    return success_response(
        data={
            "id": admin.id,
            "name": admin.full_name,
            "email": admin.email,
            "phone": admin.phone,
            "role": "ADMIN",
        }
    )


@admin_bp.put("/profile/password")
@admin_authorized
def change_password():
    admin = get_authorized_admin()
    data = request.get_json(silent=True) or {}
    try:
        AdminPasswordService.change_password(
            admin,
            str(data.get("current_password", "")),
            str(data.get("new_password", "")),
            str(data.get("confirm_password", "")),
        )
        AdminAuditService.record(
            admin.id, "PASSWORD_CHANGED", "ADMIN_ACCOUNT", admin.id
        )
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc), 400)
    return success_response("Password changed successfully.")


@admin_bp.get("/dashboard")
@admin_authorized
def dashboard():
    try:
        start, end = _window()
    except ValueError as exc:
        return error_response(str(exc), 400)

    order_scope = [Order.created_at >= start, Order.created_at < end]
    previous_length = end - start
    previous_start = start - previous_length

    total_customers = Account.query.filter_by(role=UserRole.CUSTOMER).count()
    total_suppliers = Account.query.filter_by(role=UserRole.SUPPLIER).count()
    total_logistics = Account.query.filter_by(role=UserRole.LOGISTICS_MANAGER).count()
    total_products = Product.query.count()
    active_products = Product.query.filter(Product.status == "ACTIVE").count()
    total_orders = Order.query.count()
    total_delivered_orders = Order.query.filter(
        Order.status == OrderStatus.DELIVERED
    ).count()
    total_revenue = (
        db.session.query(func.coalesce(func.sum(Order.total), 0))
        .filter(Order.status == OrderStatus.DELIVERED)
        .scalar()
    )
    order_count = Order.query.filter(*order_scope).count()
    delivered = Order.query.filter(
        *order_scope, Order.status == OrderStatus.DELIVERED
    ).count()
    revenue = (
        db.session.query(func.coalesce(func.sum(Order.total), 0))
        .filter(*order_scope, Order.status == OrderStatus.DELIVERED)
        .scalar()
    )
    payment_total = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.status == "SUCCESS",
        )
        .scalar()
    )
    pending_payouts = (
        db.session.query(func.coalesce(func.sum(SupplierPayout.amount), 0))
        .filter(SupplierPayout.status.in_(["PENDING", "PROCESSING"]))
        .scalar()
    )

    new_customers = Account.query.filter(
        Account.role == UserRole.CUSTOMER,
        Account.created_at >= start,
        Account.created_at < end,
    ).count()
    old_customers = Account.query.filter(
        Account.role == UserRole.CUSTOMER,
        Account.created_at >= previous_start,
        Account.created_at < start,
    ).count()
    new_suppliers = Account.query.filter(
        Account.role == UserRole.SUPPLIER,
        Account.created_at >= start,
        Account.created_at < end,
    ).count()
    old_suppliers = Account.query.filter(
        Account.role == UserRole.SUPPLIER,
        Account.created_at >= previous_start,
        Account.created_at < start,
    ).count()
    old_orders = Order.query.filter(
        Order.created_at >= previous_start,
        Order.created_at < start,
    ).count()

    return success_response(
        data={
            "period": {"start": start, "end": end - timedelta(microseconds=1)},
            "totals": {
                "customers": total_customers,
                "suppliers": total_suppliers,
                "logistics_users": total_logistics,
                "products": total_products,
                "active_products": active_products,
                "orders": total_orders,
                "delivered_orders": total_delivered_orders,
                "revenue": float(total_revenue or 0),
            },
            "period_metrics": {
                "orders": order_count,
                "delivered_orders": delivered,
                "revenue": float(revenue or 0),
                "payments": float(payment_total or 0),
                "pending_payouts": float(pending_payouts or 0),
            },
            "growth": {
                "customers_percent": _growth(new_customers, old_customers),
                "suppliers_percent": _growth(new_suppliers, old_suppliers),
                "orders_percent": _growth(order_count, old_orders),
            },
        }
    )


@admin_bp.get("/analytics")
@admin_authorized
def analytics():
    try:
        start, end = _window()
    except ValueError as exc:
        return error_response(str(exc), 400)

    period = end - start
    previous_start = start - period

    order_q = Order.query.filter(Order.created_at >= start, Order.created_at < end)
    delivered_q = order_q.filter(Order.status == OrderStatus.DELIVERED)

    orders = order_q.count()
    delivered = delivered_q.count()
    revenue = (
        db.session.query(func.coalesce(func.sum(Order.total), 0))
        .filter(
            Order.created_at >= start,
            Order.created_at < end,
            Order.status == OrderStatus.DELIVERED,
        )
        .scalar()
    )
    payments = Payment.query.filter(
        Payment.created_at >= start,
        Payment.created_at < end,
        Payment.status == "SUCCESS",
    ).count()
    payment_total = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.status == "SUCCESS",
        )
        .scalar()
    )
    payout_pending = (
        db.session.query(func.coalesce(func.sum(SupplierPayout.amount), 0))
        .filter(SupplierPayout.status.in_(["PENDING", "PROCESSING"]))
        .scalar()
    )
    payout_paid = (
        db.session.query(func.coalesce(func.sum(SupplierPayout.amount), 0))
        .filter(
            SupplierPayout.status == "PAID",
            SupplierPayout.created_at >= start,
            SupplierPayout.created_at < end,
        )
        .scalar()
    )

    current_customers = Account.query.filter(
        Account.role == UserRole.CUSTOMER,
        Account.created_at >= start,
        Account.created_at < end,
    ).count()
    previous_customers = Account.query.filter(
        Account.role == UserRole.CUSTOMER,
        Account.created_at >= previous_start,
        Account.created_at < start,
    ).count()
    current_suppliers = Account.query.filter(
        Account.role == UserRole.SUPPLIER,
        Account.created_at >= start,
        Account.created_at < end,
    ).count()
    previous_suppliers = Account.query.filter(
        Account.role == UserRole.SUPPLIER,
        Account.created_at >= previous_start,
        Account.created_at < start,
    ).count()

    old_orders = Order.query.filter(
        Order.created_at >= previous_start,
        Order.created_at < start,
    ).count()
    old_revenue = (
        db.session.query(func.coalesce(func.sum(Order.total), 0))
        .filter(
            Order.created_at >= previous_start,
            Order.created_at < start,
            Order.status == OrderStatus.DELIVERED,
        )
        .scalar()
    )

    step_days = 7 if period.days <= 90 else 30
    trend = []
    cursor = start
    while cursor < end:
        bucket_end = min(cursor + timedelta(days=step_days), end)
        bucket_orders = Order.query.filter(
            Order.created_at >= cursor,
            Order.created_at < bucket_end,
        ).count()
        bucket_delivered = Order.query.filter(
            Order.created_at >= cursor,
            Order.created_at < bucket_end,
            Order.status == OrderStatus.DELIVERED,
        ).count()
        bucket_revenue = (
            db.session.query(func.coalesce(func.sum(Order.total), 0))
            .filter(
                Order.created_at >= cursor,
                Order.created_at < bucket_end,
                Order.status == OrderStatus.DELIVERED,
            )
            .scalar()
        )
        trend.append(
            {
                "start": cursor,
                "end": bucket_end - timedelta(microseconds=1),
                "orders": bucket_orders,
                "delivered_orders": bucket_delivered,
                "revenue": float(bucket_revenue or 0),
            }
        )
        cursor = bucket_end

    return success_response(
        data={
            "filters": {
                "start_date": start,
                "end_date": end - timedelta(microseconds=1),
            },
            "summary": {
                "customers": Account.query.filter(
                    Account.role == UserRole.CUSTOMER,
                    Account.created_at < end,
                ).count(),
                "suppliers": Account.query.filter(
                    Account.role == UserRole.SUPPLIER,
                    Account.created_at < end,
                ).count(),
                "logistics_users": Account.query.filter(
                    Account.role == UserRole.LOGISTICS_MANAGER,
                    Account.created_at < end,
                ).count(),
                "products": Product.query.count(),
                "active_products": Product.query.filter(
                    Product.status == "ACTIVE"
                ).count(),
                "orders": orders,
                "delivered_orders": delivered,
                "revenue": float(revenue or 0),
                "payment_count": payments,
                "payment_total": float(payment_total or 0),
                "pending_payouts": float(payout_pending or 0),
                "paid_payouts": float(payout_paid or 0),
            },
            "growth": {
                "orders_percent": _growth(orders, old_orders),
                "revenue_percent": _growth(revenue, old_revenue),
                "customers_percent": _growth(current_customers, previous_customers),
                "suppliers_percent": _growth(current_suppliers, previous_suppliers),
            },
            "trend": trend,
        }
    )


@admin_bp.get("/customers")
@admin_authorized
def customers():
    search = str(request.args.get("search", "")).strip()
    query = Account.query.filter(Account.role == UserRole.CUSTOMER)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Account.full_name.ilike(pattern),
                Account.email.ilike(pattern),
                Account.phone.ilike(pattern),
            )
        )
    page = _paginate(query.order_by(Account.created_at.desc()))
    return success_response(
        data={
            "customers": [_account_payload(a) for a in page.items],
            "statuses": ["ACTIVE", "PENDING", "SUSPENDED"],
            "pagination": _pagination(page),
        }
    )


@admin_bp.put("/customers/<int:customer_id>/status")
@admin_authorized
def customer_status(customer_id):
    admin = get_authorized_admin()
    customer = Account.query.filter_by(id=customer_id, role=UserRole.CUSTOMER).first()
    if not customer:
        return error_response("Customer not found.", 404)

    status = str((request.get_json(silent=True) or {}).get("status", "")).upper()
    if status not in {"ACTIVE", "PENDING", "SUSPENDED"}:
        return error_response("Invalid customer status.", 400)

    previous = customer.status.value
    customer.status = UserStatus[status]
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "CUSTOMER_STATUS_CHANGED",
        "CUSTOMER",
        customer.id,
        {"from": previous, "to": status},
    )
    return success_response(
        "Customer status updated.",
        {"id": customer.id, "status": customer.status.value},
    )


@admin_bp.get("/suppliers")
@admin_authorized
def suppliers():
    search = str(request.args.get("search", "")).strip()
    query = Account.query.filter(Account.role == UserRole.SUPPLIER)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Account.full_name.ilike(pattern),
                Account.email.ilike(pattern),
                Account.phone.ilike(pattern),
            )
        )
    query = (
        db.session.query(Account, SellerVerification, SupplierPayoutAccount)
        .outerjoin(SellerVerification, SellerVerification.account_id == Account.id)
        .outerjoin(
            SupplierPayoutAccount,
            SupplierPayoutAccount.account_id == Account.id,
        )
        .filter(Account.role == UserRole.SUPPLIER)
    )
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Account.full_name.ilike(pattern),
                Account.email.ilike(pattern),
                Account.phone.ilike(pattern),
                SellerVerification.business_name.ilike(pattern),
                SellerVerification.gst_number.ilike(pattern),
            )
        )

    page_number = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 25, type=int), 1), 100)
    pagination = query.order_by(Account.created_at.desc()).paginate(
        page=page_number,
        per_page=per_page,
        error_out=False,
    )
    rows = []
    for account, verification, payout in pagination.items:
        rows.append(
            {
                **_account_payload(account),
                "business_name": verification.business_name if verification else None,
                "gst_number": verification.gst_number if verification else None,
                "registration_fee_paid": bool(
                    verification and verification.registration_fee_paid
                ),
                "registration_status": (
                    verification.status if verification else "PENDING"
                ),
                "payout_account_verified": bool(payout and payout.is_verified),
                "payout_eligible": bool(
                    account.status == UserStatus.ACTIVE
                    and verification
                    and verification.registration_fee_paid
                    and payout
                    and payout.is_verified
                ),
            }
        )
    return success_response(
        data={
            "suppliers": rows,
            "statuses": ["ACTIVE", "PENDING", "SUSPENDED"],
            "verification_statuses": ["PENDING", "APPROVED", "REJECTED"],
            "pagination": _pagination(pagination),
        }
    )


@admin_bp.put("/suppliers/<int:supplier_id>/status")
@admin_authorized
def supplier_status(supplier_id):
    admin = get_authorized_admin()
    supplier = Account.query.filter_by(id=supplier_id, role=UserRole.SUPPLIER).first()
    if not supplier:
        return error_response("Supplier not found.", 404)

    status = str((request.get_json(silent=True) or {}).get("status", "")).upper()
    if status not in {"ACTIVE", "PENDING", "SUSPENDED"}:
        return error_response("Invalid supplier status.", 400)

    verification = SellerVerification.query.filter_by(account_id=supplier.id).first()
    if status == "ACTIVE" and not (verification and verification.registration_fee_paid):
        return error_response(
            "Supplier cannot be activated before the registration fee is verified.",
            409,
        )

    previous = supplier.status.value
    supplier.status = UserStatus[status]
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "SUPPLIER_STATUS_CHANGED",
        "SUPPLIER",
        supplier.id,
        {"from": previous, "to": status},
    )
    return success_response(
        "Supplier status updated.", {"id": supplier.id, "status": status}
    )


@admin_bp.put("/suppliers/<int:supplier_id>/verification")
@admin_authorized
def supplier_verification(supplier_id):
    admin = get_authorized_admin()
    supplier = Account.query.filter_by(id=supplier_id, role=UserRole.SUPPLIER).first()
    if not supplier:
        return error_response("Supplier not found.", 404)
    row = SellerVerification.query.filter_by(account_id=supplier.id).first()
    if not row:
        return error_response("Supplier onboarding record not found.", 404)

    status = str((request.get_json(silent=True) or {}).get("status", "")).upper()
    if status not in {"PENDING", "APPROVED", "REJECTED"}:
        return error_response("Invalid verification status.", 400)

    previous = row.status
    row.status = status
    if status == "REJECTED" and supplier.status == UserStatus.ACTIVE:
        supplier.status = UserStatus.SUSPENDED
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "SUPPLIER_VERIFICATION_CHANGED",
        "SUPPLIER",
        supplier.id,
        {"from": previous, "to": status},
    )
    return success_response(
        "Supplier verification updated.",
        {"id": supplier.id, "status": status},
    )


@admin_bp.get("/logistics")
@admin_authorized
def logistics():
    search = str(request.args.get("search", "")).strip()
    query = Account.query.filter(Account.role == UserRole.LOGISTICS_MANAGER)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Account.full_name.ilike(pattern),
                Account.email.ilike(pattern),
                Account.phone.ilike(pattern),
            )
        )
    page = _paginate(query.order_by(Account.created_at.desc()))
    return success_response(
        data={
            "logistics_users": [_account_payload(a) for a in page.items],
            "statuses": ["ACTIVE", "SUSPENDED"],
            "pagination": _pagination(page),
        }
    )


@admin_bp.post("/logistics")
@admin_authorized
def create_logistics():
    admin = get_authorized_admin()
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if len(full_name) < 2 or not email or len(password) < 12:
        return error_response(
            "Full name, email and password (minimum 12 characters) are required.",
            400,
        )
    if Account.query.filter(func.lower(Account.email) == email).first():
        return error_response("Email already registered.", 409)

    account = Account(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.LOGISTICS_MANAGER,
        status=UserStatus.ACTIVE,
    )
    db.session.add(account)
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "LOGISTICS_USER_CREATED",
        "LOGISTICS_MANAGER",
        account.id,
        {"email": email},
    )
    return success_response("Logistics user created.", _account_payload(account), 201)


@admin_bp.put("/logistics/<int:logistics_id>/status")
@admin_authorized
def logistics_status(logistics_id):
    admin = get_authorized_admin()
    account = Account.query.filter_by(
        id=logistics_id, role=UserRole.LOGISTICS_MANAGER
    ).first()
    if not account:
        return error_response("Logistics user not found.", 404)

    status = str((request.get_json(silent=True) or {}).get("status", "")).upper()
    if status not in {"ACTIVE", "SUSPENDED"}:
        return error_response("Invalid logistics status.", 400)

    previous = account.status.value
    account.status = UserStatus[status]
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "LOGISTICS_ACCESS_CHANGED",
        "LOGISTICS_MANAGER",
        account.id,
        {"from": previous, "to": status},
    )
    return success_response(
        "Logistics access updated.", {"id": account.id, "status": status}
    )


@admin_bp.get("/banners")
@admin_authorized
def banners():
    rows = AdminBanner.query.order_by(
        AdminBanner.placement.asc(),
        AdminBanner.sort_order.asc(),
        AdminBanner.id.asc(),
    ).all()
    return success_response(data=[AdminBannerService.serialize(r) for r in rows])


@admin_bp.post("/banners/upload")
@admin_authorized
def upload_banner_image():
    image = request.files.get("image")
    if image is None or not image.filename:
        return error_response("Banner image is required.", 400)

    filename = str(image.filename).strip().lower()
    extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
    if extension not in {"jpg", "jpeg", "png", "webp"}:
        return error_response("Use a JPG, PNG or WebP image.", 400)

    # Keep banner uploads bounded even when the global Flask limit is not set.
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        return error_response("Banner image must be 10 MB or smaller.", 413)

    try:
        result = CloudinaryService.upload_image(
            image,
            folder="clipcart/banners",
        )
    except Exception:
        current_app.logger.exception("Banner image upload failed")
        return error_response("Banner image upload failed. Please try again.", 502)

    return success_response("Banner image uploaded.", result, 201)


@admin_bp.post("/banners")
@admin_authorized
def create_banner():
    admin = get_authorized_admin()
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    image_url = str(data.get("image_url", "")).strip()
    if not title:
        return error_response("Banner title is required.", 400)
    if not image_url:
        return error_response("Upload a banner image before saving.", 400)
    try:
        destination = AdminBannerService.validate_destination(data.get("destination"))
        placement = AdminBannerService.validate_placement(data.get("placement"))
        starts_at = _parse_banner_datetime(data.get("starts_at"))
        ends_at = _parse_banner_datetime(data.get("ends_at"))
    except ValueError as exc:
        return error_response(str(exc), 400)
    if starts_at and ends_at and starts_at > ends_at:
        return error_response("Banner start date cannot be after end date.", 400)

    try:
        sort_order = int(data.get("sort_order", 0))
    except (TypeError, ValueError):
        return error_response("Sort order must be a whole number.", 400)

    row = AdminBanner(
        title=title[:255],
        subtitle=str(data.get("subtitle", "")).strip()[:500] or None,
        image_url=image_url[:1000],
        cta_label=str(data.get("cta_label", "")).strip()[:100] or None,
        destination=destination,
        placement=placement,
        is_active=_coerce_bool(data.get("is_active", True), default=True),
        starts_at=starts_at,
        ends_at=ends_at,
        sort_order=sort_order,
    )
    db.session.add(row)
    db.session.commit()
    AdminAuditService.record(admin.id, "BANNER_CREATED", "BANNER", row.id)
    return success_response("Banner created.", AdminBannerService.serialize(row), 201)


@admin_bp.put("/banners/<int:banner_id>")
@admin_authorized
def update_banner(banner_id):
    admin = get_authorized_admin()
    row = AdminBanner.query.get(banner_id)
    if not row:
        return error_response("Banner not found.", 404)

    data = request.get_json(silent=True) or {}
    if "title" in data:
        row.title = str(data["title"]).strip()[:255]
        if not row.title:
            return error_response("Banner title is required.", 400)
    if "image_url" in data:
        image_url = str(data.get("image_url") or "").strip()
        if not image_url:
            return error_response("Banner image cannot be empty.", 400)
        row.image_url = image_url[:1000]
    for key, max_len in (("subtitle", 500), ("cta_label", 100)):
        if key in data:
            setattr(row, key, str(data.get(key) or "").strip()[:max_len] or None)
    if "destination" in data:
        try:
            row.destination = AdminBannerService.validate_destination(
                data["destination"]
            )
        except ValueError as exc:
            return error_response(str(exc), 400)
    if "placement" in data:
        try:
            row.placement = AdminBannerService.validate_placement(data["placement"])
        except ValueError as exc:
            return error_response(str(exc), 400)
    if "starts_at" in data:
        try:
            row.starts_at = _parse_banner_datetime(data["starts_at"])
        except ValueError as exc:
            return error_response(str(exc), 400)
    if "ends_at" in data:
        try:
            row.ends_at = _parse_banner_datetime(data["ends_at"])
        except ValueError as exc:
            return error_response(str(exc), 400)
    if row.starts_at and row.ends_at and row.starts_at > row.ends_at:
        return error_response("Banner start date cannot be after end date.", 400)
    if "is_active" in data:
        try:
            row.is_active = _coerce_bool(data["is_active"], default=row.is_active)
        except ValueError as exc:
            return error_response(str(exc), 400)
    if "sort_order" in data:
        try:
            row.sort_order = int(data["sort_order"])
        except (TypeError, ValueError):
            return error_response("Sort order must be a whole number.", 400)

    db.session.commit()
    AdminAuditService.record(admin.id, "BANNER_UPDATED", "BANNER", row.id)
    return success_response("Banner updated.", AdminBannerService.serialize(row))


@admin_bp.delete("/banners/<int:banner_id>/permanent")
@admin_authorized
def delete_banner(banner_id):
    admin = get_authorized_admin()
    row = AdminBanner.query.get(banner_id)
    if not row:
        return error_response("Banner not found.", 404)

    resource_id = row.id
    db.session.delete(row)
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "BANNER_DELETED",
        "BANNER",
        resource_id,
    )
    return success_response("Banner deleted.")


@admin_bp.delete("/banners/<int:banner_id>")
@admin_authorized
def deactivate_banner(banner_id):
    admin = get_authorized_admin()
    row = AdminBanner.query.get(banner_id)
    if not row:
        return error_response("Banner not found.", 404)
    row.is_active = False
    db.session.commit()
    AdminAuditService.record(admin.id, "BANNER_DEACTIVATED", "BANNER", row.id)
    return success_response("Banner deactivated.")


@admin_bp.get("/settings")
@admin_authorized
def settings():
    rows = PlatformSetting.query.order_by(PlatformSetting.key.asc()).all()
    return success_response(
        data=[
            {
                "key": row.key,
                "value": row.value,
                "is_public": row.is_public,
                "description": row.description,
            }
            for row in rows
        ]
    )


@admin_bp.put("/settings/<string:key>")
@admin_authorized
def update_setting(key):
    admin = get_authorized_admin()
    data = request.get_json(silent=True) or {}
    try:
        row = PlatformSettingsService.upsert(
            key,
            data.get("value"),
            is_public=data.get("is_public"),
            description=data.get("description"),
        )
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc), 400)

    AdminAuditService.record(
        admin.id,
        "PLATFORM_SETTING_CHANGED",
        "PLATFORM_SETTING",
        key,
        {"value_changed": True},
    )
    return success_response(
        "Platform setting updated.",
        {
            "key": row.key,
            "value": row.value,
            "is_public": row.is_public,
            "description": row.description,
        },
    )


@admin_bp.get("/products")
@admin_authorized
def admin_products():
    admin = get_authorized_admin()
    query = Product.query.filter(Product.seller_id == admin.id).order_by(
        Product.created_at.desc()
    )
    search = str(request.args.get("search", "")).strip()
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )
    page = _paginate(query)
    return success_response(
        data={
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "highlights": p.highlights or [],
                    "specifications": p.specifications or {},
                    "sku": p.sku,
                    "price": float(p.price or 0),
                    "compare_price": (
                        float(p.compare_price) if p.compare_price is not None else None
                    ),
                    "stock": int(p.stock or 0),
                    "status": p.status,
                    "is_featured": bool(p.is_featured),
                    "category_id": p.category_id,
                    "brand_id": p.brand_id,
                    "created_at": p.created_at,
                }
                for p in page.items
            ],
            "pagination": _pagination(page),
        }
    )


@admin_bp.post("/products")
@admin_authorized
def create_admin_product():
    admin = get_authorized_admin()
    data = request.get_json(silent=True) or {}
    try:
        payload = _validate_product_input(data, admin_id=admin.id)
        from app.modules.products.services import ProductService

        product = Product(
            **payload,
            slug=ProductService._unique_slug(payload["name"]),
        )
        db.session.add(product)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc), 400)

    AdminAuditService.record(admin.id, "ADMIN_PRODUCT_CREATED", "PRODUCT", product.id)
    return success_response(
        "Admin product created.",
        {"id": product.id, "name": product.name},
        201,
    )


@admin_bp.put("/products/<int:product_id>")
@admin_authorized
def update_admin_product(product_id):
    admin = get_authorized_admin()
    product = Product.query.filter_by(id=product_id, seller_id=admin.id).first()
    if not product:
        return error_response("Admin product not found.", 404)

    try:
        payload = _validate_product_input(
            request.get_json(silent=True) or {}, product, admin.id
        )
        for key in payload:
            if key != "seller_id":
                setattr(product, key, payload[key])
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc), 400)

    AdminAuditService.record(admin.id, "ADMIN_PRODUCT_UPDATED", "PRODUCT", product.id)
    return success_response("Admin product updated.", {"id": product.id})


@admin_bp.delete("/products/<int:product_id>")
@admin_authorized
def deactivate_admin_product(product_id):
    admin = get_authorized_admin()
    product = Product.query.filter_by(id=product_id, seller_id=admin.id).first()
    if not product:
        return error_response("Admin product not found.", 404)

    product.status = "INACTIVE"
    product.is_featured = False
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "ADMIN_PRODUCT_DEACTIVATED",
        "PRODUCT",
        product.id,
    )
    return success_response("Admin product deactivated.")


@admin_bp.get("/catalog/categories")
@admin_authorized
def catalog_categories():
    return success_response(
        data=[
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "parent_id": row.parent_id,
            }
            for row in Category.query.order_by(Category.name.asc()).all()
        ]
    )


@admin_bp.post("/catalog/categories")
@admin_authorized
def create_category():
    admin = get_authorized_admin()
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    slug = str(data.get("slug", name.lower().replace(" ", "-"))).strip().lower()
    if not name or not slug:
        return error_response("Category name and slug are required.", 400)
    if Category.query.filter(func.lower(Category.name) == name.lower()).first():
        return error_response("Category already exists.", 409)
    if Category.query.filter(func.lower(Category.slug) == slug).first():
        return error_response("Category slug already exists.", 409)
    parent_id = data.get("parent_id")
    if parent_id is not None and not Category.query.get(int(parent_id)):
        return error_response("Parent category does not exist.", 400)

    row = Category(name=name[:150], slug=slug[:200], parent_id=parent_id)
    db.session.add(row)
    db.session.commit()
    AdminAuditService.record(admin.id, "CATEGORY_CREATED", "CATEGORY", row.id)
    return success_response("Category created.", {"id": row.id, "name": row.name}, 201)


@admin_bp.put("/catalog/categories/<int:category_id>")
@admin_authorized
def update_category(category_id):
    admin = get_authorized_admin()
    row = Category.query.get(category_id)
    if not row:
        return error_response("Category not found.", 404)

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", row.name)).strip()
    slug = str(data.get("slug", row.slug)).strip().lower()
    if not name or not slug:
        return error_response("Category name and slug are required.", 400)
    if Category.query.filter(
        func.lower(Category.name) == name.lower(),
        Category.id != row.id,
    ).first():
        return error_response("Category name already exists.", 409)
    if Category.query.filter(
        func.lower(Category.slug) == slug,
        Category.id != row.id,
    ).first():
        return error_response("Category slug already exists.", 409)

    row.name = name[:150]
    row.slug = slug[:200]
    db.session.commit()
    AdminAuditService.record(admin.id, "CATEGORY_UPDATED", "CATEGORY", row.id)
    return success_response("Category updated.")


@admin_bp.get("/catalog/brands")
@admin_authorized
def catalog_brands():
    return success_response(
        data=[
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "logo_url": row.logo_url,
                "description": row.description,
                "is_active": row.is_active,
            }
            for row in Brand.query.order_by(Brand.name.asc()).all()
        ]
    )


@admin_bp.post("/catalog/brands")
@admin_authorized
def create_brand():
    admin = get_authorized_admin()
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    slug = str(data.get("slug", name.lower().replace(" ", "-"))).strip().lower()
    if not name or not slug:
        return error_response("Brand name and slug are required.", 400)
    if Brand.query.filter(func.lower(Brand.name) == name.lower()).first():
        return error_response("Brand already exists.", 409)
    if Brand.query.filter(func.lower(Brand.slug) == slug).first():
        return error_response("Brand slug already exists.", 409)

    row = Brand(
        name=name[:150],
        slug=slug[:180],
        logo_url=str(data.get("logo_url", "")).strip()[:500] or None,
        description=str(data.get("description", "")).strip()[:5000] or None,
        is_active=_coerce_bool(data.get("is_active", True), default=True),
    )
    db.session.add(row)
    db.session.commit()
    AdminAuditService.record(admin.id, "BRAND_CREATED", "BRAND", row.id)
    return success_response("Brand created.", {"id": row.id, "name": row.name}, 201)


@admin_bp.put("/catalog/brands/<int:brand_id>")
@admin_authorized
def update_brand(brand_id):
    admin = get_authorized_admin()
    row = Brand.query.get(brand_id)
    if not row:
        return error_response("Brand not found.", 404)

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", row.name)).strip()
    slug = str(data.get("slug", row.slug)).strip().lower()
    if not name or not slug:
        return error_response("Brand name and slug are required.", 400)

    if Brand.query.filter(
        func.lower(Brand.name) == name.lower(),
        Brand.id != row.id,
    ).first():
        return error_response("Brand name already exists.", 409)
    if Brand.query.filter(
        func.lower(Brand.slug) == slug,
        Brand.id != row.id,
    ).first():
        return error_response("Brand slug already exists.", 409)

    row.name = name[:150]
    row.slug = slug[:180]
    row.logo_url = str(data.get("logo_url", row.logo_url or "")).strip()[:500] or None
    row.description = (
        str(data.get("description", row.description or "")).strip()[:5000] or None
    )
    if "is_active" in data:
        try:
            row.is_active = _coerce_bool(data["is_active"], default=row.is_active)
        except ValueError as exc:
            return error_response(str(exc), 400)
    db.session.commit()
    AdminAuditService.record(admin.id, "BRAND_UPDATED", "BRAND", row.id)
    return success_response("Brand updated.")


@admin_bp.get("/payouts")
@admin_authorized
def payouts():
    status = str(request.args.get("status", "")).strip().upper()
    query = SupplierPayout.query.order_by(SupplierPayout.created_at.desc())
    if status:
        if status not in {"PENDING", "PROCESSING", "PAID", "FAILED"}:
            return error_response("Invalid payout status.", 400)
        query = query.filter(SupplierPayout.status == status)

    page = _paginate(query)
    return success_response(
        data={
            "payouts": [
                {
                    "id": row.id,
                    "supplier_id": row.account_id,
                    "payout_account_id": row.payout_account_id,
                    "amount": float(row.amount),
                    "status": row.status,
                    "reference_id": row.reference_id,
                    "created_at": row.created_at,
                    "processed_at": row.processed_at,
                }
                for row in page.items
            ],
            "statuses": ["PENDING", "PROCESSING", "PAID", "FAILED"],
            "pagination": _pagination(page),
        }
    )


@admin_bp.put("/payouts/<int:payout_id>/status")
@admin_authorized
def payout_status(payout_id):
    admin = get_authorized_admin()
    row = SupplierPayout.query.get(payout_id)
    if not row:
        return error_response("Payout not found.", 404)

    status = str((request.get_json(silent=True) or {}).get("status", "")).upper()
    if status not in {"PROCESSING", "PAID", "FAILED"}:
        return error_response("Invalid payout status.", 400)
    if row.status == "PAID":
        return error_response("This payout has already been completed.", 409)

    if status == "PAID":
        row.reference_id = row.reference_id or f"CLP-PAY-{row.id:08d}"
        row.processed_at = datetime.utcnow()

    previous = row.status
    row.status = status
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "PAYOUT_STATUS_CHANGED",
        "SUPPLIER_PAYOUT",
        row.id,
        {"supplier_id": row.account_id, "from": previous, "to": status},
    )
    try:
        AdminNotificationService.payout_updated(row, status)
    except Exception:
        db.session.rollback()

    return success_response(
        "Payout status updated.",
        {
            "id": row.id,
            "status": row.status,
            "reference_id": row.reference_id,
            "processed_at": row.processed_at,
        },
    )


@admin_bp.get("/notifications")
@admin_authorized
def admin_notifications():
    admin = get_authorized_admin()
    query = Notification.query.filter_by(account_id=admin.id).order_by(
        Notification.created_at.desc()
    )
    page = _paginate(query, default=50)
    unread = Notification.query.filter_by(account_id=admin.id, is_read=False).count()
    return success_response(
        data={
            "notifications": [
                {
                    "id": row.id,
                    "title": row.title,
                    "message": row.message,
                    "type": row.notification_type,
                    "is_read": row.is_read,
                    "created_at": row.created_at,
                }
                for row in page.items
            ],
            "unread_count": unread,
            "pagination": _pagination(page),
        }
    )


@admin_bp.put("/notifications/<int:notification_id>/read")
@admin_authorized
def read_notification(notification_id):
    admin = get_authorized_admin()
    try:
        NotificationService.read(admin.id, notification_id)
    except ValueError as exc:
        return error_response(str(exc), 404)
    return success_response("Notification marked as read.")


@admin_bp.delete("/notifications/<int:notification_id>")
@admin_authorized
def delete_notification(notification_id):
    admin = get_authorized_admin()
    try:
        NotificationService.delete(admin.id, notification_id)
    except ValueError as exc:
        return error_response(str(exc), 404)
    db.session.commit()
    AdminAuditService.record(
        admin.id,
        "NOTIFICATION_DELETED",
        "NOTIFICATION",
        notification_id,
        commit=False,
    )
    db.session.commit()
    return success_response("Notification deleted.")


@admin_bp.put("/notifications/read-all")
@admin_authorized
def read_all_notifications():
    admin = get_authorized_admin()
    Notification.query.filter_by(account_id=admin.id, is_read=False).update(
        {"is_read": True}, synchronize_session=False
    )
    db.session.commit()
    return success_response("All notifications marked as read.")


@admin_bp.get("/notifications/unread-count")
@admin_authorized
def unread_count():
    admin = get_authorized_admin()
    return success_response(
        data={
            "count": Notification.query.filter_by(
                account_id=admin.id, is_read=False
            ).count()
        }
    )


@admin_bp.get("/audit-logs")
@admin_authorized
def audit_logs():
    query = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc())
    page = _paginate(query, default=50)
    return success_response(
        data={
            "logs": [
                {
                    "id": row.id,
                    "admin_account_id": row.admin_account_id,
                    "action": row.action,
                    "resource_type": row.resource_type,
                    "resource_id": row.resource_id,
                    "metadata": row.details or {},
                    "created_at": row.created_at,
                }
                for row in page.items
            ],
            "pagination": _pagination(page),
        }
    )
