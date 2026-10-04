from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.modules.products.models import Product
from .models import WishlistItem


class WishlistRepository:

    @staticmethod
    def get(account_id):

        return (
            WishlistItem.query.options(
                joinedload(WishlistItem.product).options(
                    selectinload(Product.category),
                    selectinload(Product.images),
                )
            )
            .filter_by(account_id=account_id)
            .all()
        )

    @staticmethod
    def get_item(account_id, product_id):

        return WishlistItem.query.filter_by(
            account_id=account_id,
            product_id=product_id,
        ).first()

    @staticmethod
    def create(item):

        db.session.add(item)
        db.session.commit()

        return item

    @staticmethod
    def delete(item):

        db.session.delete(item)
        db.session.commit()
