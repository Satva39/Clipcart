from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.modules.accounts.decorators import customer_required
from app.utils.response import success_response, error_response
from .services import ReviewService

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/reviews")


@reviews_bp.get("/product/<int:product_id>")
def product_reviews(product_id):
    return success_response(data=ReviewService.get_product_reviews(product_id))


@reviews_bp.get("/mine")
@customer_required
def my_reviews():
    return success_response(
        data=ReviewService.list_for_customer(
            int(get_jwt_identity()), request.args.get("product_id", type=int)
        )
    )


@reviews_bp.post("/")
@customer_required
def create_review():
    data = request.get_json(silent=True) or {}
    try:
        review = ReviewService.create_review(
            account_id=int(get_jwt_identity()),
            product_id=data.get("product_id"),
            rating=data.get("rating"),
            review=data.get("review"),
            title=data.get("title"),
            order_item_id=data.get("order_item_id"),
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(
        data={"review_id": review.id},
        message="Review submitted. It will be auto-published after about 2 minutes.",
        status_code=201,
    )


@reviews_bp.put("/<int:review_id>")
@customer_required
def edit_review(review_id):
    data = request.get_json(silent=True) or {}
    try:
        review = ReviewService.edit_review(
            int(get_jwt_identity()),
            review_id,
            data.get("rating"),
            data.get("title"),
            data.get("review"),
        )
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(
        data={"review": ReviewService._serialize(review)},
        message="Review updated. It will be auto-published after about 2 minutes.",
    )


@reviews_bp.delete("/<int:review_id>")
@customer_required
def delete_review(review_id):
    try:
        ReviewService.delete_review(int(get_jwt_identity()), review_id)
    except ValueError as exc:
        return error_response(message=str(exc), status_code=400)
    return success_response(message="Review deleted.")
