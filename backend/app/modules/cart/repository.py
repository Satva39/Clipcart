from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.modules.products.models import Product
from .models import CartItem


class CartRepository:

    @staticmethod
    def get(account_id):

        return (
            CartItem.query.options(
                joinedload(CartItem.product).options(
                    selectinload(Product.category),
                    selectinload(Product.brand),
                    selectinload(Product.images),
                ),
                joinedload(CartItem.variant),
            )
            .filter_by(account_id=account_id)
            .all()
        )

    @staticmethod
    def get_item(
        account_id,
        product_id,
        variant_id=None,
    ):

        return CartItem.query.filter_by(
            account_id=account_id,
            product_id=product_id,
            variant_id=variant_id,
        ).first()

    @staticmethod
    def create(item):

        db.session.add(item)
        db.session.commit()

        return item

    @staticmethod
    def update():

        db.session.commit()

    @staticmethod
    def delete(item):

        db.session.delete(item)
        db.session.commit()
