from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.modules.order_items.models import OrderItem
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.modules.products.models import Product


class TrendingService:
    VALID_STATUSES = [
        OrderStatus.PAID,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    ]

    @staticmethod
    def get_trending_rows(limit=4):
        purchase_quantity = func.sum(OrderItem.quantity).label("purchase_quantity")
        results = (
            db.session.query(Product, purchase_quantity)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .options(
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.images),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.status.in_(TrendingService.VALID_STATUSES))
            .filter(Product.status == "ACTIVE")
            .group_by(Product.id)
            .order_by(purchase_quantity.desc())
            .limit(limit)
            .all()
        )
        return results

    @staticmethod
    def get_trending_products(limit=4):
        results = TrendingService.get_trending_rows(limit=limit)
        return [
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "price": float(product.price),
                "compare_price": (
                    float(product.compare_price)
                    if product.compare_price is not None
                    else None
                ),
                "stock": int(product.stock or 0),
                "category": product.category.name if product.category else None,
                "brand": (
                    {
                        "id": product.brand.id,
                        "name": product.brand.name,
                        "slug": product.brand.slug,
                        "logo_url": product.brand.logo_url,
                    }
                    if product.brand
                    else None
                ),
                "featured": bool(product.is_featured),
                "image": (
                    next(
                        (
                            image.image_url
                            for image in product.images
                            if image.is_thumbnail
                        ),
                        None,
                    )
                    or (product.images[0].image_url if product.images else None)
                ),
                "purchase_quantity": int(purchase_count or 0),
            }
            for product, purchase_count in results
        ]
