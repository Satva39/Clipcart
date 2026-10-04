from .models import ProductImage
from .repository import ProductImageRepository

from app.modules.products.models import Product
from app.extensions import db


class ProductImageService:

    @staticmethod
    def add_image(
        seller_id,
        product_id,
        image_url,
        public_id,
        variant_id=None,
        is_thumbnail=False,
    ):

        product = Product.query.get(product_id)

        if not product:
            raise ValueError("Product not found.")

        if product.seller_id != seller_id:
            raise ValueError("Unauthorized.")

        sort_order = len(
            ProductImageRepository.get_by_product(product_id)
        )

        if is_thumbnail:

            ProductImage.query.filter_by(
                product_id=product_id
            ).update(
                {"is_thumbnail": False}
            )

        image = ProductImage(
            product_id=product_id,
            variant_id=variant_id,
            image_url=image_url,
            public_id=public_id,
            sort_order=sort_order,
            is_thumbnail=is_thumbnail,
        )

        return ProductImageRepository.create(image)

    @staticmethod
    def get_product_images(product_id):

        return ProductImageRepository.get_by_product(product_id)

    @staticmethod
    def delete_image(seller_id, image_id):

        image = ProductImageRepository.get(image_id)

        if not image:
            raise ValueError("Image not found.")

        if image.product.seller_id != seller_id:
            raise ValueError("Unauthorized.")

        ProductImageRepository.delete(image)

    @staticmethod
    def set_thumbnail(
        seller_id,
        image_id,
    ):

        image = ProductImageRepository.get(image_id)

        if not image:
            raise ValueError("Image not found.")

        if image.product.seller_id != seller_id:
            raise ValueError("Unauthorized.")

        ProductImage.query.filter_by(
            product_id=image.product_id
        ).update(
            {"is_thumbnail": False}
        )

        image.is_thumbnail = True

        db.session.commit()

        return image

    @staticmethod
    def reorder_images(
        seller_id,
        image_ids,
    ):

        for index, image_id in enumerate(image_ids):

            image = ProductImageRepository.get(image_id)

            if not image:
                continue

            if image.product.seller_id != seller_id:
                raise ValueError("Unauthorized.")

            image.sort_order = index

        db.session.commit()