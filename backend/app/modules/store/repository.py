from sqlalchemy import case, func, or_
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from app.extensions import db
from app.modules.brands.models import Brand
from app.modules.categories.models import Category
from app.modules.order_items.models import OrderItem
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.modules.product_images.models import ProductImage
from app.modules.product_variants.models import ProductVariant
from app.modules.products.models import Product
from app.modules.reviews.models import Review

VALID_SOLD_STATUSES = [
    OrderStatus.PAID,
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
]


def _rating_expression():
    return (
        db.session.query(func.avg(Review.rating))
        .filter(
            Review.product_id == Product.id,
            Review.is_approved.is_(True),
        )
        .correlate(Product)
        .scalar_subquery()
    )


def _review_count_expression():
    return (
        db.session.query(func.count(Review.id))
        .filter(
            Review.product_id == Product.id,
            Review.is_approved.is_(True),
        )
        .correlate(Product)
        .scalar_subquery()
    )


def _sold_quantity_expression():
    return (
        db.session.query(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            OrderItem.product_id == Product.id,
            Order.status.in_(VALID_SOLD_STATUSES),
        )
        .correlate(Product)
        .scalar_subquery()
    )


def _discount_expression():
    return case(
        (
            Product.compare_price.isnot(None)
            & (Product.compare_price > 0)
            & (Product.compare_price > Product.price),
            ((Product.compare_price - Product.price) / Product.compare_price * 100),
        ),
        else_=0,
    )


class StoreRepository:
    @staticmethod
    def _query_with_metrics():
        rating = _rating_expression()
        review_count = _review_count_expression()
        sold_quantity = _sold_quantity_expression()
        discount_percent = _discount_expression()

        return (
            Product.query.filter(Product.status == "ACTIVE")
            .outerjoin(Brand, Brand.id == Product.brand_id)
            .outerjoin(Category, Category.id == Product.category_id)
            .options(
                contains_eager(Product.brand),
                contains_eager(Product.category),
                selectinload(Product.images),
            )
            .add_columns(
                rating.label("rating"),
                review_count.label("review_count"),
                sold_quantity.label("sold_quantity"),
                discount_percent.label("discount_percent"),
            )
        )

    @staticmethod
    def get_products(limit=40):
        rows = (
            StoreRepository._query_with_metrics()
            .order_by(Product.created_at.desc())
            .limit(limit)
            .all()
        )
        return rows

    @staticmethod
    def get_product_by_slug(slug):
        return (
            Product.query.options(
                joinedload(Product.seller),
                joinedload(Product.brand),
                joinedload(Product.category),
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.images),
                selectinload(Product.reviews),
            )
            .filter_by(slug=slug, status="ACTIVE")
            .first()
        )

    @staticmethod
    def get_product_by_id(product_id):
        return (
            Product.query.options(
                joinedload(Product.seller),
                joinedload(Product.brand),
                joinedload(Product.category),
                selectinload(Product.images),
                selectinload(Product.variants).selectinload(ProductVariant.images),
                selectinload(Product.reviews),
            )
            .filter_by(id=product_id, status="ACTIVE")
            .first()
        )

    @staticmethod
    def get_product_images(product_id):
        return (
            ProductImage.query.filter_by(product_id=product_id)
            .order_by(ProductImage.sort_order.asc())
            .all()
        )

    @staticmethod
    def get_product_variants(product_id):
        return (
            ProductVariant.query.filter_by(product_id=product_id)
            .order_by(ProductVariant.id.asc())
            .all()
        )

    @staticmethod
    def get_categories():
        return Category.query.order_by(Category.name.asc()).all()

    @staticmethod
    def get_brands():
        return (
            Brand.query.filter(Brand.is_active.is_(True))
            .order_by(Brand.name.asc())
            .all()
        )

    @staticmethod
    def get_category_products(slug):
        return (
            StoreRepository._query_with_metrics()
            .filter(Category.slug == slug)
            .order_by(Product.created_at.desc())
            .all()
        )

    @staticmethod
    def get_home_products(kind, limit=4):
        query = StoreRepository._query_with_metrics()
        rating = _rating_expression()
        sold_quantity = _sold_quantity_expression()
        discount_percent = _discount_expression()

        if kind == "featured":
            query = query.filter(Product.is_featured.is_(True))
            query = query.order_by(Product.created_at.desc())
        elif kind == "newest":
            query = query.order_by(Product.created_at.desc())
        elif kind == "deals":
            query = query.filter(
                Product.compare_price.isnot(None),
                Product.compare_price > Product.price,
            ).order_by(discount_percent.desc(), Product.created_at.desc())
        elif kind == "popular":
            query = query.order_by(
                sold_quantity.desc(),
                rating.desc().nullslast(),
                Product.created_at.desc(),
            )
        else:
            query = query.order_by(Product.created_at.desc())

        return query.limit(limit).all()

    @staticmethod
    def search_products(filters):
        query = StoreRepository._query_with_metrics()

        q = str(filters.get("q") or "").strip()
        if q:
            wildcard = f"%{q}%"
            query = query.filter(
                or_(
                    Product.name.ilike(wildcard),
                    Product.sku.ilike(wildcard),
                    Brand.name.ilike(wildcard),
                    Category.name.ilike(wildcard),
                )
            )

        category = str(filters.get("category") or "").strip()
        if category:
            if category.isdigit():
                query = query.filter(Product.category_id == int(category))
            else:
                query = query.filter(Category.slug == category)

        brand = str(filters.get("brand") or "").strip()
        if brand:
            if brand.isdigit():
                query = query.filter(Product.brand_id == int(brand))
            else:
                query = query.filter(Brand.slug == brand)

        min_price = filters.get("min_price")
        if min_price is not None:
            query = query.filter(Product.price >= min_price)

        max_price = filters.get("max_price")
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        min_rating = filters.get("min_rating")
        if min_rating is not None:
            rating = _rating_expression()
            query = query.filter(func.coalesce(rating, 0) >= min_rating)

        if filters.get("in_stock"):
            query = query.filter(Product.stock > 0)

        if filters.get("discount"):
            query = query.filter(
                Product.compare_price.isnot(None),
                Product.compare_price > Product.price,
            )

        discount_min = filters.get("discount_min")
        if discount_min is not None:
            query = query.filter(_discount_expression() >= discount_min)

        if filters.get("has_variants"):
            variant_exists = (
                db.session.query(ProductVariant.id)
                .filter(ProductVariant.product_id == Product.id)
                .exists()
            )
            query = query.filter(variant_exists)

        sort = filters.get("sort")
        rating = _rating_expression()
        sold_quantity = _sold_quantity_expression()
        discount_percent = _discount_expression()

        if sort == "price_asc":
            query = query.order_by(Product.price.asc(), Product.id.asc())
        elif sort == "price_desc":
            query = query.order_by(Product.price.desc(), Product.id.asc())
        elif sort == "newest":
            query = query.order_by(Product.created_at.desc(), Product.id.desc())
        elif sort == "popular":
            query = query.order_by(
                sold_quantity.desc(),
                rating.desc().nullslast(),
                Product.created_at.desc(),
            )
        elif sort == "rating":
            query = query.order_by(
                rating.desc().nullslast(),
                _review_count_expression().desc(),
                Product.created_at.desc(),
            )
        elif sort == "discount":
            query = query.order_by(
                discount_percent.desc(),
                Product.created_at.desc(),
            )
        else:
            query = query.order_by(
                sold_quantity.desc(),
                rating.desc().nullslast(),
                Product.created_at.desc(),
            )

        page = max(int(filters.get("page") or 1), 1)
        limit = min(max(int(filters.get("limit") or 24), 1), 60)

        return query.paginate(
            page=page,
            per_page=limit,
            error_out=False,
        )

    @staticmethod
    def get_recommendation_candidates(viewed_ids, seed_product_id=None, limit=4):
        viewed = {int(value) for value in (viewed_ids or []) if str(value).isdigit()}

        seed_ids = list(viewed)
        if seed_product_id and str(seed_product_id).isdigit():
            seed_ids.append(int(seed_product_id))

        seed_products = (
            Product.query.filter(
                Product.id.in_(seed_ids),
                Product.status == "ACTIVE",
            ).all()
            if seed_ids
            else []
        )

        category_ids = {product.category_id for product in seed_products}
        brand_ids = {
            product.brand_id
            for product in seed_products
            if product.brand_id is not None
        }

        query = StoreRepository._query_with_metrics()
        sold_quantity = _sold_quantity_expression()
        rating = _rating_expression()

        if viewed:
            query = query.filter(~Product.id.in_(viewed))

        if category_ids or brand_ids:
            match_conditions = []
            if category_ids:
                match_conditions.append(Product.category_id.in_(category_ids))
            if brand_ids:
                match_conditions.append(Product.brand_id.in_(brand_ids))

            query = query.filter(or_(*match_conditions))
            query = query.order_by(
                Product.is_featured.desc(),
                sold_quantity.desc(),
                rating.desc().nullslast(),
                Product.created_at.desc(),
            )
        else:
            query = query.filter(Product.is_featured.is_(True)).order_by(
                sold_quantity.desc(),
                rating.desc().nullslast(),
                Product.created_at.desc(),
            )

        return query.limit(limit).all()
