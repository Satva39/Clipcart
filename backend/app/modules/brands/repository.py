from app.extensions import db

from .models import Brand


class BrandRepository:

    @staticmethod
    def get_all():
        return Brand.query.filter_by(is_active=True).order_by(Brand.name.asc()).all()

    @staticmethod
    def get_by_id(brand_id):
        return Brand.query.get(brand_id)

    @staticmethod
    def get_by_slug(slug):
        return Brand.query.filter_by(
            slug=slug,
            is_active=True,
        ).first()

    @staticmethod
    def create(brand):
        db.session.add(brand)
        db.session.commit()

        return brand

    @staticmethod
    def update():
        db.session.commit()

    @staticmethod
    def delete(brand):
        db.session.delete(brand)
        db.session.commit()
