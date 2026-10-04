from app.extensions import db
from .models import Notification


class NotificationRepository:

    @staticmethod
    def create(notification):
        db.session.add(notification)
        db.session.flush()
        return notification

    @staticmethod
    def get_all(account_id):
        return (
            Notification.query.filter_by(account_id=account_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    @staticmethod
    def get(notification_id):
        return Notification.query.get(notification_id)

    @staticmethod
    def unread_count(account_id):
        return Notification.query.filter_by(
            account_id=account_id,
            is_read=False,
        ).count()

    @staticmethod
    def save():
        db.session.commit()

    @staticmethod
    def delete(notification):
        db.session.delete(notification)
        db.session.commit()
