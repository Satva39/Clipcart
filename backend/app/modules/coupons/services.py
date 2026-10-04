from datetime import datetime
from decimal import Decimal

from .enums import DiscountType
from .models import Coupon
from .repository import CouponRepository
from app.core.business_rules import money


class CouponService:
    @staticmethod
    def create(data, seller_id):
        code = str(data.get("code", "")).strip().upper()
        if not code:
            raise ValueError("Coupon code is required.")
        if CouponRepository.get_by_code(code):
            raise ValueError("Coupon already exists.")

        try:
            discount_type = DiscountType(data["discount_type"])
        except (KeyError, ValueError):
            raise ValueError("Invalid discount type.")

        coupon = Coupon(
            seller_id=seller_id,
            code=code,
            discount_type=discount_type,
            discount_value=money(data["discount_value"]),
            minimum_order=money(data.get("minimum_order", 0)),
            maximum_discount=(
                money(data["maximum_discount"])
                if data.get("maximum_discount") is not None
                else None
            ),
            usage_limit=int(data.get("usage_limit", 0) or 0),
            expires_at=data.get("expires_at"),
            is_active=bool(data.get("is_active", True)),
        )
        return CouponRepository.create(coupon)

    @staticmethod
    def validate(code, order_total, coupon=None):
        normalized = str(code or "").strip().upper()
        coupon = coupon or CouponRepository.get_by_code(normalized)
        if not coupon:
            raise ValueError("Invalid coupon.")
        if not coupon.is_active:
            raise ValueError("Coupon inactive.")
        if coupon.expires_at and coupon.expires_at < datetime.utcnow():
            raise ValueError("Coupon expired.")
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            raise ValueError("Coupon usage exceeded.")
        if money(order_total) < money(coupon.minimum_order):
            raise ValueError("Minimum order not reached.")
        return coupon

    @staticmethod
    def calculate_discount(coupon, eligible_total):
        base = money(eligible_total)
        if base <= 0:
            return Decimal("0.00")

        if coupon.discount_type == DiscountType.PERCENTAGE:
            discount = money(base * money(coupon.discount_value) / Decimal("100"))
        elif coupon.discount_type == DiscountType.FIXED:
            discount = money(coupon.discount_value)
        else:
            raise ValueError("Invalid discount type.")

        if coupon.maximum_discount is not None:
            discount = min(discount, money(coupon.maximum_discount))
        return min(discount, base)
