from app.extensions import db
from .models import ProductVariant


class ProductVariantRepository:

    @staticmethod
    def create(variant):
        db.session.add(variant)
        db.session.commit()
        return variant

    @staticmethod
    def get_by_product(product_id):
        return ProductVariant.query.filter_by(
            product_id=product_id
        ).all()