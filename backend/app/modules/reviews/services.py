from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.modules.order_items.models import OrderItem
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order

from .models import Review
from .repository import ReviewRepository


class ReviewService:
    @staticmethod
    def _serialize(review):
        return {
            "id": review.id,
            "account_id": review.account_id,
            "product_id": review.product_id,
            "order_item_id": review.order_item_id,
            "rating": review.rating,
            "title": review.title,
            "review": review.review,
            "verified_purchase": review.is_verified_purchase,
            "approved": review.is_approved,
            "customer": review.account.full_name if review.account else "Customer",
            "created_at": review.created_at,
            "updated_at": review.updated_at,
        }

    @staticmethod
    def auto_approve_pending(max_age_minutes=2):
        """Approve reviews once they have waited the automatic moderation window."""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        pending = Review.query.filter(
            Review.is_approved.is_(False),
            Review.created_at <= cutoff,
        ).all()
        if not pending:
            return 0

        for item in pending:
            item.is_approved = True

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return len(pending)

    @staticmethod
    def get_product_reviews(product_id):
        ReviewService.auto_approve_pending()
        reviews = ReviewRepository.get_product_reviews(product_id)
        counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for item in reviews:
            counts[int(item.rating)] = counts.get(int(item.rating), 0) + 1
        total = len(reviews)
        average = (
            round(sum(int(item.rating) for item in reviews) / total, 2) if total else 0
        )
        return {
            "reviews": [ReviewService._serialize(review) for review in reviews],
            "summary": {
                "average": average,
                "count": total,
                "distribution": counts,
            },
        }

    @staticmethod
    def list_for_customer(account_id, product_id=None):
        ReviewService.auto_approve_pending()
        query = Review.query.filter_by(account_id=account_id)
        if product_id:
            query = query.filter_by(product_id=product_id)
        return [
            ReviewService._serialize(review)
            for review in query.order_by(Review.created_at.desc()).all()
        ]

    @staticmethod
    def create_review(account_id, product_id, order_item_id, rating, title, review):
        try:
            rating = int(rating)
            product_id = int(product_id)
            order_item_id = int(order_item_id)
        except (TypeError, ValueError):
            raise ValueError("Invalid review details.")

        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5.")
        title = str(title or "").strip()[:255] or None
        review = str(review or "").strip()
        if not review:
            raise ValueError("Review text is required.")
        if len(review) > 5000:
            raise ValueError("Review is too long.")

        order_item = (
            OrderItem.query.join(Order)
            .filter(
                OrderItem.id == order_item_id,
                OrderItem.product_id == product_id,
                Order.id == OrderItem.order_id,
                Order.account_id == account_id,
                Order.status == OrderStatus.DELIVERED,
            )
            .first()
        )
        if not order_item:
            raise ValueError(
                "Only customers who purchased and received this item can review it."
            )

        existing = Review.query.filter_by(order_item_id=order_item_id).first()
        if existing:
            raise ValueError("Review already submitted for this purchase.")

        new_review = Review(
            account_id=account_id,
            product_id=product_id,
            order_item_id=order_item_id,
            rating=rating,
            title=title,
            review=review,
            is_verified_purchase=True,
            is_approved=False,
        )
        db.session.add(new_review)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Review already submitted for this purchase.")
        return new_review

    @staticmethod
    def edit_review(account_id, review_id, rating, title, review):
        item = Review.query.filter_by(id=review_id, account_id=account_id).first()
        if not item:
            raise ValueError("Review not found.")
        if item.is_approved:
            raise ValueError("Approved reviews cannot be edited.")
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            raise ValueError("Invalid rating.")
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5.")
        body = str(review or "").strip()
        if not body:
            raise ValueError("Review text is required.")
        item.rating = rating
        item.title = str(title or "").strip()[:255] or None
        item.review = body[:5000]
        db.session.commit()
        return item

    @staticmethod
    def delete_review(account_id, review_id):
        item = Review.query.filter_by(id=review_id, account_id=account_id).first()
        if not item:
            raise ValueError("Review not found.")
        db.session.delete(item)
        db.session.commit()
