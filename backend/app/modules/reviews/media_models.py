from app.extensions import db
from app.shared.models.base_model import BaseModel


class ReviewMedia(BaseModel):
    __tablename__ = "review_media"

    review_id = db.Column(
        db.Integer,
        db.ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    media_type = db.Column(db.String(20), nullable=False)
    media_url = db.Column(db.Text, nullable=False)
    public_id = db.Column(db.Text, nullable=False)
    resource_type = db.Column(db.String(20), nullable=False, default="image")
    mime_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    review = db.relationship("Review", back_populates="media")
