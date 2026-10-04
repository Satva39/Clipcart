from .models import Order
from app.extensions import db


class OrderRepository:

    @staticmethod
    def create(order):
        db.session.add(order)
        db.session.commit()
        return order

    @staticmethod
    def get_by_id(order_id):
        return Order.query.get(order_id)

    @staticmethod
    def get_by_account(account_id):
        return (
            Order.query
            .filter_by(account_id=account_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    @staticmethod
    def update():
        db.session.commit()

    @staticmethod
    def get_all():
    
        return (
            Order.query
            .order_by(Order.created_at.desc())
            .all()
        )