from sqlalchemy.exc import IntegrityError

from .models import Notification
from .enums import NotificationType
from .repository import NotificationRepository


class NotificationService:
    @staticmethod
    def create(
        account_id, title, message, notification_type, dedupe_key=None, commit=True
    ):
        if dedupe_key:
            existing = Notification.query.filter_by(dedupe_key=dedupe_key).first()
            if existing:
                return existing

        notification = Notification(
            account_id=account_id,
            title=title,
            message=message,
            notification_type=notification_type,
            dedupe_key=dedupe_key,
        )
        try:
            result = NotificationRepository.create(notification)
            if commit:
                from app.extensions import db

                db.session.commit()
            return result
        except IntegrityError:
            from app.extensions import db

            db.session.rollback()
            if dedupe_key:
                existing = Notification.query.filter_by(dedupe_key=dedupe_key).first()
                if existing:
                    return existing
            raise

    @staticmethod
    def list(account_id):
        notifications = NotificationRepository.get_all(account_id)
        return [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.notification_type,
                "is_read": n.is_read,
                "created_at": n.created_at,
            }
            for n in notifications
        ]

    @staticmethod
    def read(account_id, notification_id):
        notification = NotificationRepository.get(notification_id)
        if not notification:
            raise ValueError("Notification not found.")
        if notification.account_id != account_id:
            raise ValueError("Unauthorized.")
        notification.is_read = True
        NotificationRepository.save()

    @staticmethod
    def read_all(account_id):
        notifications = NotificationRepository.get_all(account_id)
        for n in notifications:
            n.is_read = True
        NotificationRepository.save()

    @staticmethod
    def delete(account_id, notification_id):
        notification = NotificationRepository.get(notification_id)
        if not notification:
            raise ValueError("Notification not found.")
        if notification.account_id != account_id:
            raise ValueError("Unauthorized.")
        NotificationRepository.delete(notification)

    @staticmethod
    def notify_logistics(title, message, dedupe_key_prefix=None):
        """Create an operational notification for every active logistics manager."""
        from app.modules.accounts.enums import UserRole, UserStatus
        from app.modules.accounts.models import Account

        managers = Account.query.filter(
            Account.role == UserRole.LOGISTICS_MANAGER,
            Account.status == UserStatus.ACTIVE,
        ).all()

        created = []
        for manager in managers:
            key = f"{dedupe_key_prefix}:{manager.id}" if dedupe_key_prefix else None
            created.append(
                NotificationService.create(
                    account_id=manager.id,
                    title=title,
                    message=message,
                    notification_type=NotificationType.LOGISTICS,
                    dedupe_key=key,
                    commit=False,
                )
            )
        return created

    @staticmethod
    def unread(account_id):
        return NotificationRepository.unread_count(account_id)
