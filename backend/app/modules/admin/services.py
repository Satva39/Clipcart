from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.modules.accounts.models import Account
from app.modules.notifications.models import Notification
from app.services.communication.email_service import EmailService


class AdminNotificationService:
    @staticmethod
    def _admin_account():
        admin_email = current_app.config.get("CLIPCART_ADMIN_EMAIL", "")
        if not admin_email:
            return None
        from app.modules.accounts.enums import UserRole, UserStatus

        return Account.query.filter(
            Account.email.ilike(admin_email),
            Account.role == UserRole.ADMIN,
            Account.status == UserStatus.ACTIVE,
        ).first()

    @staticmethod
    def notify(
        title,
        message,
        notification_type="SYSTEM",
        dedupe_key=None,
        commit=True,
    ):
        admin = AdminNotificationService._admin_account()
        if not admin:
            return None

        existing = None
        if dedupe_key:
            existing = Notification.query.filter_by(dedupe_key=dedupe_key).first()
            if existing:
                return existing

        notification = Notification(
            account_id=admin.id,
            title=str(title)[:255],
            message=str(message),
            notification_type=str(notification_type)[:50],
            is_read=False,
            dedupe_key=dedupe_key,
        )
        db.session.add(notification)
        db.session.flush()
        if commit:
            db.session.commit()
        return notification

    @staticmethod
    def supplier_registered(account):
        return AdminNotificationService.notify(
            "New supplier registration",
            f"Supplier #{account.id} ({account.full_name}) is awaiting onboarding completion.",
            "SELLER",
            f"supplier:{account.id}:registered",
        )

    @staticmethod
    def supplier_payment(account, amount):
        return AdminNotificationService.notify(
            "Supplier onboarding payment received",
            f"Supplier #{account.id} completed the ₹{float(amount):,.2f} registration payment.",
            "PAYMENT",
            f"supplier:{account.id}:registration-paid",
        )

    @staticmethod
    def payout_updated(payout, status):
        return AdminNotificationService.notify(
            "Supplier payout updated",
            f"Payout #{payout.id} for supplier #{payout.account_id} is now {status.lower()}.",
            "PAYMENT",
            f"payout:{payout.id}:status:{status}",
        )

    @staticmethod
    def delivery_updated(order_id, event):
        return AdminNotificationService.notify(
            "Delivery update",
            f"Order #{order_id}: {event}.",
            "LOGISTICS",
            f"order:{order_id}:admin:{event}",
        )


class AdminAuditService:
    @staticmethod
    def record(
        admin_account_id,
        action,
        resource_type,
        resource_id=None,
        metadata=None,
        commit=True,
    ):
        from app.modules.admin.models import AdminAuditLog

        row = AdminAuditLog(
            admin_account_id=admin_account_id,
            action=str(action)[:80],
            resource_type=str(resource_type)[:80],
            resource_id=str(resource_id)[:100] if resource_id is not None else None,
            details=metadata or {},
        )
        db.session.add(row)
        db.session.flush()
        if commit:
            db.session.commit()
        return row


class PlatformSettingsService:
    DEFAULTS = {
        "marketing_fee": (2.0, False),
        "tax_threshold": (2000.0, False),
        "tax_rate": (0.18, False),
        "tax_cap": (500.0, False),
        "supplier_registration_fee": (50.0, False),
        "customer_announcement": ("", True),
    }

    NUMERIC_LIMITS = {
        "marketing_fee": (Decimal("0"), None),
        "tax_threshold": (Decimal("0"), None),
        "tax_rate": (Decimal("0"), Decimal("1")),
        "tax_cap": (Decimal("0"), None),
        "supplier_registration_fee": (Decimal("0.01"), None),
    }

    @classmethod
    def get(cls, key, default=None):
        from app.modules.admin.models import PlatformSetting

        row = PlatformSetting.query.filter_by(key=key).first()
        if row:
            return row.value
        configured = cls.DEFAULTS.get(key)
        return configured[0] if configured else default

    @classmethod
    def get_decimal(cls, key):
        value = cls.get(key, "0")
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid platform setting: {key}")

    @classmethod
    def public_settings(cls):
        from app.modules.admin.models import PlatformSetting

        rows = (
            PlatformSetting.query.filter_by(is_public=True)
            .order_by(PlatformSetting.key.asc())
            .all()
        )
        return {row.key: row.value for row in rows}

    @classmethod
    def upsert(cls, key, value, is_public=None, description=None):
        from app.modules.admin.models import PlatformSetting

        if key not in cls.DEFAULTS:
            raise ValueError("Unsupported platform setting.")

        if is_public and key != "customer_announcement":
            raise ValueError("Only customer-facing content settings may be public.")

        if key in cls.NUMERIC_LIMITS:
            try:
                numeric = Decimal(str(value))
            except (InvalidOperation, ValueError):
                raise ValueError("Setting value must be numeric.")
            minimum, maximum = cls.NUMERIC_LIMITS[key]
            if minimum is not None and numeric < minimum:
                raise ValueError("Setting value is below the allowed minimum.")
            if maximum is not None and numeric > maximum:
                raise ValueError("Setting value is above the allowed maximum.")
            normalized = float(numeric)
        elif key == "customer_announcement":
            normalized = str(value or "").strip()[:500]
        else:
            normalized = value

        row = PlatformSetting.query.filter_by(key=key).first()
        if row is None:
            default_public = bool(cls.DEFAULTS[key][1])
            row = PlatformSetting(key=key, value=normalized, is_public=default_public)
            db.session.add(row)
        else:
            row.value = normalized

        if is_public is not None:
            row.is_public = bool(is_public)
        if description is not None:
            row.description = str(description)[:500]

        db.session.flush()
        return row


class AdminBannerService:
    PLACEMENTS = {
        "HOME_HERO": "Homepage hero",
        "HOME_PROMO": "Homepage promotion strip",
        "HOME_CATEGORY": "Homepage category promotion",
    }

    @classmethod
    def validate_placement(cls, placement):
        value = str(placement or "HOME_HERO").strip().upper()
        if value not in cls.PLACEMENTS:
            raise ValueError("Invalid banner placement.")
        return value

    @staticmethod
    def validate_destination(destination):
        destination = str(destination or "").strip()
        if not destination:
            return None
        lowered = destination.lower()
        if lowered.startswith(("javascript:", "data:", "vbscript:")):
            raise ValueError("Banner destination is not allowed.")
        return destination[:1000]

    @classmethod
    def _visibility_status(cls, banner):
        if not banner.image_url:
            return "MISSING_IMAGE"
        return "ACTIVE" if banner.is_active else "INACTIVE"

    @classmethod
    def serialize(cls, banner):
        return {
            "id": banner.id,
            "title": banner.title,
            "subtitle": banner.subtitle,
            "image_url": banner.image_url,
            "cta_label": banner.cta_label,
            "destination": banner.destination,
            "placement": banner.placement or "HOME_HERO",
            "is_active": bool(banner.is_active),
            "visibility_status": cls._visibility_status(banner),
            "sort_order": banner.sort_order,
            "created_at": banner.created_at,
            "updated_at": banner.updated_at,
        }

    @classmethod
    def public_active(cls, placement=None):
        from app.modules.admin.models import AdminBanner

        query = AdminBanner.query.filter(
            AdminBanner.is_active.is_(True),
            AdminBanner.image_url.isnot(None),
            AdminBanner.image_url != "",
        )
        if placement:
            query = query.filter(
                AdminBanner.placement == cls.validate_placement(placement)
            )
        rows = query.order_by(
            AdminBanner.sort_order.asc(),
            AdminBanner.id.asc(),
        ).all()
        return [cls.serialize(row) for row in rows]


class AdminPasswordService:
    @staticmethod
    def _serializer():
        return URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"],
            salt="clipcart-admin-password-reset",
        )

    @staticmethod
    def create_reset_token(account):
        return AdminPasswordService._serializer().dumps(
            {
                "account_id": account.id,
                "email": account.email,
                "purpose": "ADMIN_PASSWORD_RESET",
                "issued_at": datetime.utcnow().timestamp(),
            }
        )

    @staticmethod
    def verify_reset_token(token, max_age=None):
        max_age = max_age or int(
            current_app.config.get("ADMIN_PASSWORD_RESET_TTL", 900)
        )
        try:
            data = AdminPasswordService._serializer().loads(token, max_age=max_age)
        except (BadSignature, SignatureExpired):
            raise ValueError("Reset link is invalid or expired.")

        if data.get("purpose") != "ADMIN_PASSWORD_RESET":
            raise ValueError("Invalid reset token.")

        account = Account.query.get(data.get("account_id"))
        if not account:
            raise ValueError("Admin account not found.")

        configured_email = current_app.config.get("CLIPCART_ADMIN_EMAIL", "")
        if (
            account.role.value != "ADMIN"
            or account.status.value != "ACTIVE"
            or not configured_email
            or account.email.strip().lower() != configured_email
            or float(data.get("issued_at", 0)) < 1
            or account.updated_at.timestamp() > float(data["issued_at"]) + 1
        ):
            raise ValueError("Reset link is invalid or already used.")

        return account

    @staticmethod
    def change_password(account, current_password, new_password, confirm_password=None):
        if not check_password_hash(account.password_hash, current_password):
            raise ValueError("Current password is incorrect.")
        if len(new_password) < 12:
            raise ValueError("Password must be at least 12 characters.")
        if confirm_password is not None and new_password != confirm_password:
            raise ValueError("Passwords do not match.")

        account.password_hash = generate_password_hash(new_password)
        db.session.commit()
        return account

    @staticmethod
    def send_reset_email(account):
        token = AdminPasswordService.create_reset_token(account)
        portal_url = str(
            current_app.config.get("CLIPCART_ADMIN_PORTAL_URL", "")
        ).rstrip("/")
        if not portal_url:
            raise RuntimeError("Admin portal URL is not configured.")

        reset_url = f"{portal_url}/reset-password?token={token}"
        EmailService.send_admin_password_reset(
            account.email,
            reset_url,
            int(current_app.config.get("ADMIN_PASSWORD_RESET_TTL", 900) / 60),
        )
