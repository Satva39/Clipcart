from app.modules.products.models import Product
from app.modules.orders.models import Order
from app.modules.order_items.models import OrderItem
from app.extensions import db


class SupplierDashboardRepository:

    @staticmethod
    def get_products(supplier_id):
        return Product.query.filter_by(
            seller_id=supplier_id
        ).all()

    @staticmethod
    def get_supplier_orders(supplier_id):

        return (
            db.session.query(Order)
            .join(OrderItem)
            .join(Product)
            .filter(Product.seller_id == supplier_id)
            .distinct()
            .all()
        )