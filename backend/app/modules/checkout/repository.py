from app.extensions import db
from .models import CheckoutSession

ACTIVE_STATUSES = ("PENDING", "PAYMENT_PENDING", "PAID")


class CheckoutRepository:
    @staticmethod
    def get_active_by_account(account_id, lock=False):
        query = CheckoutSession.query.filter(
            CheckoutSession.account_id == account_id,
            CheckoutSession.payment_status.in_(ACTIVE_STATUSES),
            CheckoutSession.order_id.is_(None),
        ).order_by(CheckoutSession.created_at.desc())
        if lock:
            query = query.with_for_update()
        return query.first()

    @staticmethod
    def get_by_id(account_id, session_id, lock=False):
        query = CheckoutSession.query.filter_by(id=session_id, account_id=account_id)
        if lock:
            query = query.with_for_update()
        return query.first()

    @staticmethod
    def create(session):
        db.session.add(session)
        db.session.commit()
        return session

    @staticmethod
    def update():
        db.session.commit()
