from app.modules.brands.models import Brand
from app.modules.categories.models import Category
from app.modules.products.models import Product
from app.modules.trending.services import TrendingService
from app.modules.reviews.services import ReviewService
from app.modules.admin.services import AdminBannerService, PlatformSettingsService

from .repository import StoreRepository


def _percent_off(price, compare_price):
    if not compare_price or compare_price <= price or compare_price <= 0:
        return 0
    return round(((compare_price - price) / compare_price) * 100)


def serialize_product(row):
    # SQLAlchemy returns a Row object when the repository query uses
    # Product.query.add_columns(...). Row is not necessarily a tuple on
    # newer SQLAlchemy versions, so extract the Product entity by class key.
    if isinstance(row, tuple):
        product, rating, review_count, sold_quantity, discount_percent = row
    elif hasattr(row, "_mapping") and Product in row._mapping:
        mapping = row._mapping
        product = mapping[Product]
        rating = mapping.get("rating")
        review_count = mapping.get("review_count", 0)
        sold_quantity = mapping.get("sold_quantity", 0)
        discount_percent = mapping.get("discount_percent", 0)
    else:
        product = row
        rating = None
        review_count = 0
        sold_quantity = 0
        discount_percent = _percent_off(
            float(product.price or 0),
            float(product.compare_price or 0),
        )

    price = float(product.price or 0)
    compare_price = (
        float(product.compare_price) if product.compare_price is not None else None
    )

    image = next(
        (image.image_url for image in product.images if image.is_thumbnail),
        None,
    ) or (product.images[0].image_url if product.images else None)

    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "description": product.description,
        "price": price,
        "compare_price": compare_price,
        "discount_percent": int(round(float(discount_percent or 0))),
        "stock": int(product.stock or 0),
        "category": (
            {
                "id": product.category.id,
                "name": product.category.name,
                "slug": product.category.slug,
            }
            if product.category
            else None
        ),
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
        "image": image,
        "rating": round(float(rating), 1) if rating is not None else 0,
        "review_count": int(review_count or 0),
        "sold_quantity": int(sold_quantity or 0),
    }


class StoreService:
    @staticmethod
    def get_products():
        return StoreRepository.get_products()

    @staticmethod
    def _assemble_complete_product(product):
        review_stats = {
            "average": 0,
            "count": 0,
            "distribution": {5: 0, 4: 0, 3: 0, 2: 0, 1: 0},
        }
        if product.reviews:
            approved = [review for review in product.reviews if review.is_approved]
            if approved:
                distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
                for review in approved:
                    rating = int(review.rating)
                    if rating in distribution:
                        distribution[rating] += 1
                review_stats = {
                    "average": round(
                        sum(review.rating for review in approved) / len(approved),
                        1,
                    ),
                    "count": len(approved),
                    "distribution": distribution,
                }

        return {
            "product": product,
            "images": product.images,
            "variants": product.variants,
            "review_stats": review_stats,
        }

    @staticmethod
    def get_complete_product(slug):
        # Publish reviews that have completed the automatic two-minute window
        # before calculating the product's aggregate rating.
        ReviewService.auto_approve_pending()
        product = StoreRepository.get_product_by_slug(slug)
        if not product:
            return None
        return StoreService._assemble_complete_product(product)

    @staticmethod
    def get_categories():
        return StoreRepository.get_categories()

    @staticmethod
    def get_brands():
        return StoreRepository.get_brands()

    @staticmethod
    def get_category_products(slug):
        return StoreRepository.get_category_products(slug)

    @staticmethod
    def search(filters):
        return StoreRepository.search_products(filters)

    @staticmethod
    def get_home_data():
        # Keep storefront rating/count aggregates in sync with automatic review
        # publication without requiring an admin moderation action.
        ReviewService.auto_approve_pending()
        categories = StoreRepository.get_categories()
        brands = StoreRepository.get_brands()
        featured = StoreRepository.get_home_products("featured", 4)
        newest = StoreRepository.get_home_products("newest", 4)
        deals = StoreRepository.get_home_products("deals", 4)
        popular = StoreRepository.get_home_products("popular", 4)

        hero_rows = featured or newest
        hero = []
        for row in hero_rows[:4]:
            product = serialize_product(row)
            hero.append(
                {
                    "id": product["id"],
                    "slug": product["slug"],
                    "title": product["name"],
                    "subtitle": (
                        product["brand"]["name"]
                        if product["brand"]
                        else (
                            product["category"]["name"]
                            if product["category"]
                            else "Discover on Clipcart"
                        )
                    ),
                    "description": product["description"],
                    "image": product["image"],
                    "price": product["price"],
                    "compare_price": product["compare_price"],
                    "discount_percent": product["discount_percent"],
                }
            )

        return {
            "hero": hero,
            "banners": AdminBannerService.public_active(),
            "public_settings": PlatformSettingsService.public_settings(),
            "categories": [
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                }
                for category in categories
            ],
            "brands": [
                {
                    "id": brand.id,
                    "name": brand.name,
                    "slug": brand.slug,
                    "logo_url": brand.logo_url,
                }
                for brand in brands
            ],
            "featured": [serialize_product(row) for row in featured],
            "best_sellers": [serialize_product(row) for row in popular],
            "new_arrivals": [serialize_product(row) for row in newest],
            "deals": [serialize_product(row) for row in deals],
            "trending": [
                {
                    **serialize_product(product),
                    "sold_quantity": int(purchase_count or 0),
                }
                for product, purchase_count in TrendingService.get_trending_rows(
                    limit=4
                )
            ],
        }

    @staticmethod
    def get_recommendations(viewed_ids=None, seed_product_id=None, limit=4):
        rows = StoreRepository.get_recommendation_candidates(
            viewed_ids=viewed_ids,
            seed_product_id=seed_product_id,
            limit=limit,
        )
        return [serialize_product(row) for row in rows]

    @staticmethod
    def get_product_detail(product_id):
        ReviewService.auto_approve_pending()
        product = StoreRepository.get_product_by_id(product_id)
        if not product:
            return None

        data = StoreService._assemble_complete_product(product)
        data["product_payload"] = serialize_product(product)
        return data
