from app.extensions import db
from app.core.base_model import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"

    name = db.Column(db.String(150), nullable=False, unique=True)
    slug = db.Column(db.String(200), nullable=False, unique=True)

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id"),
        nullable=True,
    )

    children = db.relationship(
        "Category",
        backref=db.backref("parent", remote_side="Category.id"),
    )