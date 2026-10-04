from .models import WishlistItem
from .repository import WishlistRepository


class WishlistService:

    @staticmethod
    def get(account_id):

        return WishlistRepository.get(account_id)

    @staticmethod
    def add(account_id, product_id):

        item = WishlistRepository.get_item(
            account_id,
            product_id,
        )

        if item:
            return item

        item = WishlistItem(
            account_id=account_id,
            product_id=product_id,
        )

        return WishlistRepository.create(item)

    @staticmethod
    def remove(account_id, product_id):

        item = WishlistRepository.get_item(
            account_id,
            product_id,
        )

        if item:
            WishlistRepository.delete(item)