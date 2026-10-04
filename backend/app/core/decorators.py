from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.models import Account
from app.shared.utils.api_response import error


def role_required(*roles):
    """Require one of the supplied account roles."""

    allowed = {
        role.value if isinstance(role, UserRole) else str(role).upper()
        for role in roles
    }

    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = str(claims.get("role", "")).upper()
            portal = str(claims.get("portal", "")).lower()

            expected_portal = {
                UserRole.ADMIN.value: "admin",
                UserRole.SUPPLIER.value: "supplier",
                UserRole.CUSTOMER.value: "customer",
                UserRole.LOGISTICS_MANAGER.value: "logistics",
            }.get(role)

            if role not in allowed or (
                portal and expected_portal and portal != expected_portal
            ):
                return error("Permission denied.", 403)

            try:
                account_id = int(get_jwt_identity())
            except (TypeError, ValueError):
                return error("Invalid session.", 401)

            account = Account.query.get(account_id)
            if not account or account.role.value != role:
                return error("Account access is not authorized.", 403)

            # Customer accounts have no separate verification/onboarding gate in
            # Clipcart, so a legacy PENDING customer remains able to shop.
            # Supplier/logistics/admin portals keep their stricter ACTIVE check.
            if account.status in {UserStatus.SUSPENDED, UserStatus.DELETED}:
                return error("Account access is currently restricted.", 403)

            if role != UserRole.CUSTOMER.value and account.status != UserStatus.ACTIVE:
                return error("Account access is currently restricted.", 403)

            return fn(*args, **kwargs)

        return wrapped

    return decorator


def customer_required(fn):
    return role_required(UserRole.CUSTOMER)(fn)


def supplier_required(fn):
    return role_required(UserRole.SUPPLIER)(fn)


def admin_required(fn):
    from app.modules.admin.authorization import admin_authorized

    return admin_authorized(fn)


def logistics_required(fn):
    return role_required(UserRole.LOGISTICS_MANAGER)(fn)


def customer_or_supplier_required(fn):
    return role_required(UserRole.CUSTOMER, UserRole.SUPPLIER)(fn)


def active_supplier_required(fn):
    """Require a supplier account that is currently active in the database.

    The database lookup intentionally complements the JWT role claim so a supplier
    whose status was changed after login cannot continue using the portal.
    """

    @wraps(fn)
    def wrapped(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if str(claims.get("role", "")).upper() != UserRole.SUPPLIER.value:
            return error("Supplier access required.", 403)

        try:
            account_id = int(get_jwt_identity())
        except (TypeError, ValueError):
            return error("Invalid supplier session.", 401)

        account = Account.query.get(account_id)
        if not account or account.role != UserRole.SUPPLIER:
            return error("Supplier account not found.", 403)

        if account.status != UserStatus.ACTIVE:
            status = account.status.value if account.status else "UNKNOWN"
            return error(
                f"Supplier account access is currently restricted ({status}).",
                403,
            )

        return fn(*args, **kwargs)

    return wrapped


def active_logistics_required(fn):
    """Require an active logistics-manager account, not only a JWT role claim."""

    @wraps(fn)
    def wrapped(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if str(claims.get("role", "")).upper() != UserRole.LOGISTICS_MANAGER.value:
            return error("Logistics access required.", 403)

        try:
            account_id = int(get_jwt_identity())
        except (TypeError, ValueError):
            return error("Invalid logistics session.", 401)

        account = Account.query.get(account_id)
        if not account or account.role != UserRole.LOGISTICS_MANAGER:
            return error("Logistics account not found.", 403)

        if account.status != UserStatus.ACTIVE:
            status = account.status.value if account.status else "UNKNOWN"
            return error(
                f"Logistics account access is currently restricted ({status}).",
                403,
            )

        return fn(*args, **kwargs)

    return wrapped


def supplier_or_admin_required(fn):
    """Allow only an active supplier or an active authorized admin."""

    @wraps(fn)
    def wrapped(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        role = str(claims.get("role", "")).upper()
        portal = str(claims.get("portal", "")).lower()

        if role == UserRole.ADMIN.value and portal == "admin":
            from app.modules.admin.authorization import get_authorized_admin

            if get_authorized_admin():
                return fn(*args, **kwargs)
            return error("Admin access required.", 403)

        if role != UserRole.SUPPLIER.value or portal != "supplier":
            return error("Supplier or admin access required.", 403)

        try:
            account_id = int(get_jwt_identity())
        except (TypeError, ValueError):
            return error("Invalid supplier session.", 401)

        account = Account.query.get(account_id)
        if not account or account.role != UserRole.SUPPLIER:
            return error("Supplier account not found.", 403)
        if account.status != UserStatus.ACTIVE:
            return error("Supplier account access is restricted.", 403)
        return fn(*args, **kwargs)

    return wrapped
