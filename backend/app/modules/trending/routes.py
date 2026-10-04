from flask import Blueprint

from app.utils.response import success_response

from .services import TrendingService

trending_bp = Blueprint(
    "trending",
    __name__,
    url_prefix="/api/trending",
)


@trending_bp.get("/")
def get_trending_products():
    products = TrendingService.get_trending_products(limit=4)

    return success_response(data=products)
