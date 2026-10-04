from flask import Blueprint

from app.utils.response import (
    success_response,
    error_response,
)

from .services import BrandService

brands_bp = Blueprint(
    "brands",
    __name__,
    url_prefix="/api/brands",
)


@brands_bp.get("/")
def get_brands():

    brands = BrandService.get_all()

    return success_response(
        data=[
            {
                "id": brand.id,
                "name": brand.name,
                "slug": brand.slug,
                "logo_url": brand.logo_url,
                "description": brand.description,
            }
            for brand in brands
        ]
    )


@brands_bp.get("/<slug>")
def get_brand(slug):

    brand = BrandService.get_by_slug(slug)

    if not brand:
        return error_response(
            message="Brand not found.",
            status_code=404,
        )

    return success_response(
        data={
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "logo_url": brand.logo_url,
            "description": brand.description,
        }
    )
