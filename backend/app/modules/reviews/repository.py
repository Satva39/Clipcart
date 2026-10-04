from app.extensions import db
from .models import Review


class ReviewRepository:

    @staticmethod
    def create(review):
        db.session.add(review)
        db.session.commit()
        return review

    @staticmethod
    def get_product_reviews(product_id):
        return Review.query.filter_by(
            product_id=product_id,
            is_approved=True,
        ).order_by(
            Review.created_at.desc()
        ).all()