from app.extensions import db
from .models import OrderEvent


class OrderEventService:
    @staticmethod
    def add(order, event_type, title, message=None):
        event = OrderEvent(
            order_id=order.id,
            event_type=event_type,
            title=title,
            message=message,
        )
        db.session.add(event)
        return event

    @staticmethod
    def serialize(event):
        return {
            "id": event.id,
            "type": event.event_type,
            "title": event.title,
            "message": event.message,
            "occurred_at": event.occurred_at,
        }
