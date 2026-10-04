from app.extensions import db
from .models import SellerVerification


class SellerVerificationRepository:

    @staticmethod
    def create(verification):
        db.session.add(verification)
        db.session.commit()
        return verification

    @staticmethod
    def get_by_account(account_id):
        return SellerVerification.query.filter_by(
            account_id=account_id
        ).first()

    @staticmethod
    def update(verification):
        db.session.commit()
        return verification