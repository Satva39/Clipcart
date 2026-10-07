from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.modules.order_items.models import OrderItem
from app.modules.orders.enums import OrderStatus
from app.modules.orders.models import Order
from app.services.cloudinary_service import CloudinaryService

from .media_models import ReviewMedia

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
            "media": [
                {
                    "id": media.id,
                    "type": media.media_type,
                    "url": media.media_url,
                    "mime_type": media.mime_type,
                    "sort_order": media.sort_order,
                }
                for media in (review.media or [])
            ],
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
    def list_for_customer(account_id, product_id=None, order_id=None):
        ReviewService.auto_approve_pending()
        query = Review.query.filter_by(account_id=account_id)
        if product_id:
            query = query.filter_by(product_id=product_id)
        if order_id:
            query = query.join(OrderItem, Review.order_item_id == OrderItem.id).filter(
                OrderItem.order_id == int(order_id)
            )
        return [
            ReviewService._serialize(review)
            for review in query.order_by(Review.created_at.desc()).all()
        ]

    @staticmethod
    def create_review(
        account_id, product_id, order_item_id, rating, title, review, media_files=None
    ):
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

        media_files = [
            item
            for item in (media_files or [])
            if item and getattr(item, "filename", "")
        ]
        if len(media_files) > 6:
            raise ValueError("You can upload up to 6 photos or videos per review.")

        allowed_media = {
            "image/jpeg": ("image", 15 * 1024 * 1024),
            "image/png": ("image", 15 * 1024 * 1024),
            "image/webp": ("image", 15 * 1024 * 1024),
            "video/mp4": ("video", 40 * 1024 * 1024),
            "video/webm": ("video", 40 * 1024 * 1024),
            "video/quicktime": ("video", 40 * 1024 * 1024),
        }
        prepared_media = []
        total_bytes = 0
        for file in media_files:
            mimetype = str(getattr(file, "mimetype", "") or "").lower()
            if mimetype not in allowed_media:
                raise ValueError(
                    "Use JPG, PNG or WebP images, or MP4, WebM or MOV videos."
                )
            media_type, limit = allowed_media[mimetype]
            try:
                file.stream.seek(0, 2)
                size = file.stream.tell()
                file.stream.seek(0)
            except (AttributeError, OSError):
                content = file.read(limit + 1)
                file.stream.seek(0)
                size = len(content)
            if size > limit:
                raise ValueError(
                    f"Each {media_type} file must be {limit // (1024 * 1024)} MB or smaller."
                )
            total_bytes += size
            prepared_media.append((file, media_type, mimetype, size))
        if total_bytes > 60 * 1024 * 1024:
            raise ValueError("The total review media upload must be 60 MB or smaller.")

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
        uploaded_public_ids = []
        try:
            db.session.flush()
            for index, (file, media_type, mimetype, size) in enumerate(prepared_media):
                result = CloudinaryService.upload_media(
                    file,
                    folder=f"clipcart/reviews/{new_review.id}",
                )
                uploaded_public_ids.append(
                    (result["public_id"], result.get("resource_type", media_type))
                )
                db.session.add(
                    ReviewMedia(
                        review_id=new_review.id,
                        media_type=media_type,
                        media_url=result["secure_url"],
                        public_id=result["public_id"],
                        resource_type=result.get("resource_type", media_type),
                        mime_type=mimetype,
                        file_size=size,
                        sort_order=index,
                    )
                )
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            for public_id, resource_type in uploaded_public_ids:
                try:
                    CloudinaryService.delete_media(public_id, resource_type)
                except Exception:
                    pass
            raise ValueError("Review already submitted for this purchase.")
        except Exception:
            db.session.rollback()
            for public_id, resource_type in uploaded_public_ids:
                try:
                    CloudinaryService.delete_media(public_id, resource_type)
                except Exception:
                    pass
            raise ValueError(
                "Review media upload failed. Please try again with supported files."
            )
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
        media = list(item.media or [])
        db.session.delete(item)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        for asset in media:
            if asset.public_id:
                try:
                    CloudinaryService.delete_media(
                        asset.public_id, asset.resource_type or asset.media_type
                    )
                except Exception:
                    pass
