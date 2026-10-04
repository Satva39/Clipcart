from app.extensions import db
from app.shared.models.base_model import BaseModel


class Brand(BaseModel):
    __tablename__ = "brands"

    name = db.Column(
        db.String(150),
        nullable=False,
        unique=True,
    )

    slug = db.Column(
        db.String(180),
        nullable=False,
        unique=True,
    )

    logo_url = db.Column(
        db.String(500),
        nullable=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )