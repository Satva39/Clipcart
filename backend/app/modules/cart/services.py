from .models import CartItem
from .repository import CartRepository
from app.modules.products.models import Product
from app.modules.product_variants.models import ProductVariant


class CartService:

    @staticmethod
    def get(account_id):

        items = CartRepository.get(account_id)

        cart = []
        subtotal = 0
        total_items = 0

        for item in items:

            if item.variant:
                price = float(item.variant.price)
                stock = item.variant.stock
            else:
                price = float(item.product.price)
                stock = item.product.stock

            item_total = price * item.quantity

            subtotal += item_total
            total_items += item.quantity

            cart.append(
                {
                    "product_id": item.product.id,
                    "name": item.product.name,
                    "slug": item.product.slug,
                    "category": (
                        item.product.category.name if item.product.category else None
                    ),
                    "brand": (item.product.brand.name if item.product.brand else None),
                    "compare_price": (
                        float(item.product.compare_price)
                        if item.product.compare_price is not None
                        else None
                    ),
                    "variant_id": item.variant_id,
                    "variant_name": item.variant.name if item.variant else None,
                    "variant_value": item.variant.value if item.variant else None,
                    "quantity": item.quantity,
                    "price": price,
                    "stock": stock,
                    "item_total": item_total,
                    "image": (
                        item.product.images[0].image_url
                        if item.product.images
                        else None
                    ),
                }
            )

        return {
            "items": cart,
            "subtotal": subtotal,
            "total_items": total_items,
        }

    @staticmethod
    def add(
        account_id,
        product_id,
        variant_id,
        quantity,
    ):

        product = Product.query.get(product_id)

        if not product:
            raise ValueError("Product not found.")

        if product.status != "ACTIVE":
            raise ValueError("Product is unavailable.")

        if variant_id:

            variant = ProductVariant.query.get(variant_id)

            if not variant:
                raise ValueError("Variant not found.")

            available_stock = variant.stock

        else:

            available_stock = product.stock

        item = CartRepository.get_item(
            account_id,
            product_id,
            variant_id,
        )

        existing_quantity = item.quantity if item else 0

        if existing_quantity + quantity > available_stock:
            raise ValueError("Requested quantity exceeds available stock.")

        if item:
            item.quantity += quantity
            CartRepository.update()
            return item

        item = CartItem(
            account_id=account_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
        )

        return CartRepository.create(item)

    @staticmethod
    def update_quantity(
        account_id,
        product_id,
        variant_id,
        quantity,
    ):

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        item = CartRepository.get_item(
            account_id,
            product_id,
            variant_id,
        )

        if not item:
            return None

        if item.variant:
            available_stock = item.variant.stock
        else:
            available_stock = item.product.stock

        if quantity > available_stock:
            raise ValueError("Requested quantity exceeds available stock.")

        item.quantity = quantity

        CartRepository.update()

        return item

    @staticmethod
    def remove(
        account_id,
        product_id,
        variant_id,
    ):
        item = CartRepository.get_item(
            account_id,
            product_id,
            variant_id,
        )

        if item:
            CartRepository.delete(item)
