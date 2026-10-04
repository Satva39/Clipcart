from app.extensions import db
from .models import Coupon


class CouponRepository:

    @staticmethod
    def create(coupon):
        db.session.add(coupon)
        db.session.commit()
        return coupon

    @staticmethod
    def get_by_code(code):
        return Coupon.query.filter_by(code=code).first()

    @staticmethod
    def get_by_id(coupon_id):
        return Coupon.query.get(coupon_id)

    @staticmethod
    def get_all():
        return Coupon.query.order_by(Coupon.id.desc()).all()

    @staticmethod
    def update():
        db.session.commit()

    @staticmethod
    def delete(coupon):
        db.session.delete(coupon)
        db.session.commit()