from .models import ProductVariant
from .repository import ProductVariantRepository


def create_variant(
    product_id,
    name,
    value,
    sku,
    price,
    stock,
):

    variant = ProductVariant(
        product_id=product_id,
        name=name,
        value=value,
        sku=sku,
        price=price,
        stock=stock,
    )

    return ProductVariantRepository.create(variant)


def get_product_variants(product_id):
    return ProductVariantRepository.get_by_product(product_id)