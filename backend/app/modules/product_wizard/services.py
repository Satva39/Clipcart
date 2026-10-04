from app.extensions import db
from app.modules.products.services import ProductService
from app.modules.product_images.services import ProductImageService
from app.modules.product_variants.services import create_variant


class ProductWizardService:

    @staticmethod
    def create(data, seller_id):

        try:

            product = ProductService.create(
                data=data,
                seller_id=seller_id,
            )

            for image in data.get("images", []):

                ProductImageService.create(
                    product_id=product.id,
                    image_url=image["image_url"],
                    public_id=image["public_id"],
                    variant_id=None,
                    is_thumbnail=image.get("is_thumbnail", False),
                    sort_order=image.get("sort_order", 0),
                )

            for variant in data.get("variants", []):

                create_variant(
                    product_id=product.id,
                    name=variant["name"],
                    value=variant["value"],
                    sku=variant["sku"],
                    price=variant["price"],
                    stock=variant["stock"],
                )

            db.session.commit()

            return product

        except Exception:

            db.session.rollback()
            raise