from app.extensions import db
from .models import ProductImage


class ProductImageRepository:

    @staticmethod
    def create(image):
        db.session.add(image)
        db.session.commit()
        return image

    @staticmethod
    def get(image_id):
        return ProductImage.query.get(image_id)

    @staticmethod
    def get_by_product(product_id):
        return (
            ProductImage.query
            .filter_by(product_id=product_id)
            .order_by(ProductImage.sort_order.asc())
            .all()
        )

    @staticmethod
    def delete(image):
        db.session.delete(image)
        db.session.commit()

    @staticmethod
    def update():
        db.session.commit()