from app.extensions import db
from .models import InventoryLog


class InventoryRepository:

    @staticmethod
    def create(log):
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def get_logs(variant_id):
        return (
            InventoryLog.query
            .filter_by(variant_id=variant_id)
            .order_by(InventoryLog.created_at.desc())
            .all()
        )

    @staticmethod
    def get_low_stock(threshold=10):

        return (
            InventoryLog.query
            .filter(InventoryLog.change <= threshold)
            .order_by(InventoryLog.created_at.desc())
            .all()
        )