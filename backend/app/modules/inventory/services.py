from .models import InventoryLog
from .repository import InventoryRepository


class InventoryService:

    @staticmethod
    def add_stock(variant_id, quantity, reason):

        log = InventoryLog(
            variant_id=variant_id,
            change=quantity,
            reason=reason,
        )

        return InventoryRepository.create(log)

    @staticmethod
    def get_history(variant_id):
        return InventoryRepository.get_logs(variant_id)

    @staticmethod
    def low_stock(threshold=10):

        logs = InventoryRepository.get_low_stock(
            threshold
        )

        return [
            {
                "variant_id": log.variant_id,
                "stock_change": log.change,
                "reason": log.reason,
                "updated_at": log.created_at,
            }
            for log in logs
        ]