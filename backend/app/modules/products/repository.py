from app.extensions import db
from .models import Product


class ProductRepository:

    @staticmethod
    def create(product):
        db.session.add(product)
        db.session.commit()
        return product

    @staticmethod
    def get_by_slug(slug):
        return Product.query.filter_by(slug=slug).first()

    @staticmethod
    def get_by_sku(sku):
        return Product.query.filter_by(sku=sku).first()

    @staticmethod
    def get_by_id(product_id):
        return Product.query.get(product_id)

    @staticmethod
    def get_all():
        return Product.query.all()

    @staticmethod
    def search(
        search=None,
        category_id=None,
        min_price=None,
        max_price=None,
        sort=None,
        page=1,
        per_page=10,
    ):

        query = Product.query.filter_by(
            status="ACTIVE"
        )

        if search:
            query = query.filter(
                Product.name.ilike(f"%{search}%")
            )

        if category_id:
            query = query.filter_by(
                category_id=category_id
            )

        if min_price is not None:
            query = query.filter(
                Product.price >= min_price
            )

        if max_price is not None:
            query = query.filter(
                Product.price <= max_price
            )

        if sort == "price_asc":
            query = query.order_by(
                Product.price.asc()
            )

        elif sort == "price_desc":
            query = query.order_by(
                Product.price.desc()
            )

        else:
            query = query.order_by(
                Product.created_at.desc()
            )

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )

        return pagination