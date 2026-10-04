from app.extensions import db
from .models import CustomerAddress


class CustomerAddressRepository:
    @staticmethod
    def create(address):
        db.session.add(address)
        db.session.commit()
        return address

    @staticmethod
    def get_all(account_id):
        return (
            CustomerAddress.query.filter_by(account_id=account_id)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.id.desc())
            .all()
        )

    @staticmethod
    def get_by_id(address_id):
        return CustomerAddress.query.get(address_id)

    @staticmethod
    def save():
        db.session.commit()

    @staticmethod
    def delete(address):
        db.session.delete(address)
        db.session.commit()

    @staticmethod
    def clear_default(account_id, exclude_id=None):
        query = CustomerAddress.query.filter_by(account_id=account_id)
        if exclude_id is not None:
            query = query.filter(CustomerAddress.id != exclude_id)
        query.update({"is_default": False})
        db.session.commit()
