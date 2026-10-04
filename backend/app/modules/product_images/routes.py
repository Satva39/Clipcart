from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt_identity

from app.core.decorators import active_supplier_required

from app.extensions import db
from app.utils.response import (
    success_response,
    error_response,
)

from app.modules.products.models import Product
from app.modules.product_variants.models import ProductVariant
from app.services.cloudinary_service import (
    CloudinaryService,
)

from .models import ProductImage

product_images_bp = Blueprint(
    "product_images",
    __name__,
    url_prefix="/api/product-images",
)


@product_images_bp.post("/product/<int:product_id>")
@active_supplier_required
def upload_product_images(product_id):

    account_id = int(get_jwt_identity())

    product = Product.query.filter_by(
        id=product_id,
        seller_id=account_id,
    ).first()

    if not product:
        return error_response(
            message="Product not found or access denied.",
            status_code=404,
        )

    files = request.files.getlist("images")

    if not files:
        return error_response(
            message="No images selected.",
            status_code=400,
        )

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    valid_files = []
    for file in files:
        if not file or not file.filename:
            continue
        if file.mimetype not in allowed_types:
            return error_response(
                message="Use JPG, PNG or WebP image files only.",
                status_code=400,
            )
        valid_files.append(file)

    if not valid_files:
        return error_response(
            message="No valid image files were selected.",
            status_code=400,
        )

    if request.content_length and request.content_length > 20 * 1024 * 1024:
        return error_response(
            message="The total image upload must be 20 MB or smaller.",
            status_code=413,
        )

    variant_id = request.form.get(
        "variant_id",
        type=int,
    )

    if variant_id:
        variant = ProductVariant.query.filter_by(
            id=variant_id,
            product_id=product_id,
        ).first()

        if not variant:
            return error_response(
                message="Invalid product variant.",
                status_code=400,
            )

    start_order = ProductImage.query.filter_by(product_id=product_id).count()

    uploaded = []

    for index, file in enumerate(valid_files):
        try:
            result = CloudinaryService.upload_image(
                file,
                folder=f"clipcart/products/{product_id}",
            )
        except Exception:
            current_app.logger.exception(
                "Product image upload failed for product %s", product_id
            )
            db.session.rollback()
            return error_response(
                message="Image upload failed. Check the file and try again.",
                status_code=502,
            )

        image = ProductImage(
            product_id=product_id,
            variant_id=variant_id,
            image_url=result["image_url"],
            public_id=result["public_id"],
            sort_order=start_order + index,
            is_thumbnail=(index == 0 and not variant_id and start_order == 0),
        )

        db.session.add(image)

        uploaded.append(image)

    db.session.commit()

    return success_response(
        data=[
            {
                "id": image.id,
                "product_id": image.product_id,
                "variant_id": image.variant_id,
                "image_url": image.image_url,
                "public_id": image.public_id,
                "sort_order": image.sort_order,
                "is_thumbnail": image.is_thumbnail,
            }
            for image in uploaded
        ],
        message="Product images uploaded.",
        status_code=201,
    )


@product_images_bp.get("/product/<int:product_id>")
@active_supplier_required
def get_product_images(product_id):
    account_id = int(get_jwt_identity())

    product = Product.query.filter_by(
        id=product_id,
        seller_id=account_id,
    ).first()

    if not product:
        return error_response(
            message="Product not found.",
            status_code=404,
        )

    images = (
        ProductImage.query.filter_by(product_id=product_id)
        .order_by(ProductImage.sort_order.asc())
        .all()
    )

    return success_response(
        data=[
            {
                "id": image.id,
                "image_url": image.image_url,
                "public_id": image.public_id,
                "sort_order": image.sort_order,
                "is_thumbnail": image.is_thumbnail,
                "variant_id": image.variant_id,
            }
            for image in images
        ]
    )


@product_images_bp.delete("/<int:image_id>")
@active_supplier_required
def delete_product_image(image_id):
    account_id = int(get_jwt_identity())

    image = ProductImage.query.get(image_id)

    if not image:
        return error_response(
            message="Image not found.",
            status_code=404,
        )

    product = Product.query.filter_by(
        id=image.product_id,
        seller_id=account_id,
    ).first()

    if not product:
        return error_response(
            message="Unauthorized.",
            status_code=403,
        )

    if image.public_id:
        CloudinaryService.delete_image(image.public_id)

    db.session.delete(image)

    remaining = (
        ProductImage.query.filter(
            ProductImage.product_id == product.id,
            ProductImage.id != image.id,
        )
        .order_by(ProductImage.sort_order.asc())
        .all()
    )

    if remaining and image.is_thumbnail:
        remaining[0].is_thumbnail = True

    db.session.commit()

    return success_response(message="Image deleted.")


@product_images_bp.put("/product/<int:product_id>/reorder")
@active_supplier_required
def reorder_product_images(product_id):
    account_id = int(get_jwt_identity())

    product = Product.query.filter_by(
        id=product_id,
        seller_id=account_id,
    ).first()

    if not product:
        return error_response(
            message="Product not found.",
            status_code=404,
        )

    data = request.get_json(silent=True) or {}

    image_ids = data.get("image_ids", [])

    if not isinstance(image_ids, list):
        return error_response(
            message="image_ids must be an array.",
            status_code=400,
        )

    for index, image_id in enumerate(image_ids):
        image = ProductImage.query.filter_by(
            id=image_id,
            product_id=product_id,
        ).first()

        if image:
            image.sort_order = index

    db.session.commit()

    return success_response(message="Images reordered.")


@product_images_bp.put("/<int:image_id>/thumbnail")
@active_supplier_required
def set_product_thumbnail(image_id):
    account_id = int(get_jwt_identity())

    image = ProductImage.query.get(image_id)

    if not image:
        return error_response(
            message="Image not found.",
            status_code=404,
        )

    product = Product.query.filter_by(
        id=image.product_id,
        seller_id=account_id,
    ).first()

    if not product:
        return error_response(
            message="Unauthorized.",
            status_code=403,
        )

    ProductImage.query.filter_by(product_id=product.id).update({"is_thumbnail": False})

    image.is_thumbnail = True

    db.session.commit()

    return success_response(message="Primary image updated.")
