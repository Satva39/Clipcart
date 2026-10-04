from .repository import SupplierDashboardRepository


class SupplierDashboardService:

    @staticmethod
    def dashboard(supplier_id):

        products = SupplierDashboardRepository.get_products(
            supplier_id
        )

        orders = SupplierDashboardRepository.get_supplier_orders(
            supplier_id
        )

        revenue = sum(
            float(order.total)
            for order in orders
        )

        return {
            "total_products": len(products),
            "active_products": len(
                [p for p in products if p.status == "ACTIVE"]
            ),
            "out_of_stock": len(
                [p for p in products if p.stock == 0]
            ),
            "total_orders": len(orders),
            "total_revenue": revenue,
        }