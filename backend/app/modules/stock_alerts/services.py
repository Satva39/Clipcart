from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.modules.notifications.services import NotificationService
from app.modules.notifications.enums import NotificationType
from app.modules.products.models import Product
from app.modules.product_variants.models import ProductVariant
from .models import StockAlertSubscription


class StockAlertService:
    @staticmethod
    def _serialize(item):
        return {
            "id": item.id,
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "created_at": item.created_at,
        }

    @staticmethod
    def status(account_id, product_id, variant_id=None):
        item = StockAlertSubscription.query.filter_by(
            account_id=account_id,
            product_id=product_id,
            variant_id=variant_id,
        ).first()
        return {
            "subscribed": item is not None,
            "subscription": StockAlertService._serialize(item) if item else None,
        }

    @staticmethod
    def subscribe(account_id, product_id, variant_id=None):
        product = Product.query.filter_by(id=int(product_id)).first()
        if not product:
            raise ValueError("Product not found.")
        if variant_id is not None:
            variant = ProductVariant.query.filter_by(
                id=int(variant_id), product_id=product.id
            ).first()
            if not variant:
                raise ValueError("Variant not found for this product.")

        existing = StockAlertSubscription.query.filter_by(
            account_id=account_id,
            product_id=product_id,
            variant_id=variant_id,
        ).first()
        if existing:
            return StockAlertService._serialize(existing)

        item = StockAlertSubscription(
            account_id=account_id,
            product_id=product_id,
            variant_id=variant_id,
        )
        db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            existing = StockAlertSubscription.query.filter_by(
                account_id=account_id,
                product_id=product_id,
                variant_id=variant_id,
            ).first()
            if existing:
                return StockAlertService._serialize(existing)
            raise
        return StockAlertService._serialize(item)

    @staticmethod
    def unsubscribe(account_id, product_id, variant_id=None):
        item = StockAlertSubscription.query.filter_by(
            account_id=account_id,
            product_id=product_id,
            variant_id=variant_id,
        ).first()
        if item:
            db.session.delete(item)
            db.session.commit()
        return {"subscribed": False}

    @staticmethod
    def notify_available(product_id, variant_id=None):
        query = StockAlertSubscription.query.filter(
            StockAlertSubscription.product_id == product_id,
        )
        if variant_id is not None:
            query = query.filter(
                (StockAlertSubscription.variant_id == variant_id)
                | (StockAlertSubscription.variant_id.is_(None))
            )
        else:
            query = query.filter(StockAlertSubscription.variant_id.is_(None))

        subscriptions = query.all()
        for item in subscriptions:
            dedupe_key = f"stock-alert:{item.id}:{product_id}:{variant_id or 'product'}"
            NotificationService.create(
                account_id=item.account_id,
                title="Back in stock",
                message="An item you asked us to watch is available again.",
                notification_type=NotificationType.SYSTEM,
                dedupe_key=dedupe_key,
            )
            db.session.delete(item)

        if subscriptions:
            db.session.commit()
