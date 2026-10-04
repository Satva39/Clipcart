from app.extensions import db
from app.shared.models.base_model import BaseModel


class RevokedToken(BaseModel):
    __tablename__ = "revoked_tokens"

    jti = db.Column(db.String(255), unique=True, nullable=False, index=True)
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )
    token_type = db.Column(db.String(30), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    account = db.relationship(
        "Account", backref=db.backref("revoked_tokens", lazy=True)
    )
