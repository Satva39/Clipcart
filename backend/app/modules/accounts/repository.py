from sqlalchemy import func

from app.extensions import db
from .models import Account


class AccountRepository:

    @staticmethod
    def get_by_email(email):

        return Account.query.filter(func.lower(Account.email) == email.lower()).first()

    @staticmethod
    def get_by_phone(phone):
        return Account.query.filter_by(phone=phone).first()

    @staticmethod
    def save():
        db.session.commit()

    @staticmethod
    def get_by_id(account_id):

        return Account.query.get(account_id)

    @staticmethod
    def create(account):

        from app.extensions import db

        db.session.add(account)
        db.session.commit()

        return account
