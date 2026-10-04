from functools import wraps

from flask import current_app
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.modules.accounts.enums import UserRole, UserStatus
from app.modules.accounts.models import Account
from app.utils.response import error_response


def get_authorized_admin():
    claims = get_jwt()
    if str(claims.get("role", "")).upper() != UserRole.ADMIN.value:
        return None
    if str(claims.get("portal", "")).lower() != "admin":
        return None

    try:
        account_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None

    admin = Account.query.filter_by(id=account_id, role=UserRole.ADMIN).first()
    if not admin or admin.status != UserStatus.ACTIVE:
        return None

    issued_at = claims.get("iat")
    if issued_at is not None and admin.updated_at is not None:
        if admin.updated_at.timestamp() > float(issued_at):
            return None

    configured_email = (
        str(current_app.config.get("CLIPCART_ADMIN_EMAIL", "")).strip().lower()
    )
    if not configured_email or admin.email.strip().lower() != configured_email:
        return None
    return admin


def admin_authorized(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        verify_jwt_in_request()
        if not get_authorized_admin():
            return error_response("Admin access required.", 403)
        return fn(*args, **kwargs)

    return wrapped
