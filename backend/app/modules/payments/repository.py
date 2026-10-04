from app.extensions import db
from .models import Payment


class PaymentRepository:

    @staticmethod
    def create(payment):
        db.session.add(payment)
        db.session.commit()
        return payment

    @staticmethod
    def get_by_transaction(transaction_id):
        return Payment.query.filter_by(
            transaction_id=transaction_id
        ).first()

    @staticmethod
    def get_by_account(account_id):
        return Payment.query.filter_by(
            account_id=account_id
        ).all()