from flask import Blueprint
from app.utils.response import success_response, error_response
from .services import (
    get_categories,
    create_category,
    get_category,
)

from flask import request
from app.core.decorators import admin_required

categories_bp = Blueprint(
    "categories",
    __name__,
    url_prefix="/api/categories",
)


@categories_bp.get("/")
def all_categories():

    categories = get_categories()

    return success_response(
        data=[
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
            }
            for c in categories
        ]
    )


@categories_bp.get("/<int:category_id>")
def get_one(category_id):

    category = get_category(category_id)

    if not category:
        return error_response(
            message="Category not found.",
            status_code=404,
        )

    return success_response(
        data={
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "parent_id": category.parent_id,
        }
    )


@categories_bp.post("/")
@admin_required
def create():

    data = request.get_json()

    category = create_category(
        name=data["name"],
        slug=data["slug"],
        parent_id=data.get("parent_id"),
    )

    return success_response(
        message="Category created.",
        data={
            "id": category.id,
            "name": category.name,
        },
    )
