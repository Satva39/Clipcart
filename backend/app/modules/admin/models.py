from app.extensions import db
from app.shared.models.base_model import BaseModel


class AdminAuditLog(BaseModel):
    __tablename__ = "admin_audit_logs"

    admin_account_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )
    action = db.Column(db.String(80), nullable=False, index=True)
    resource_type = db.Column(db.String(80), nullable=False, index=True)
    resource_id = db.Column(db.String(100), nullable=True, index=True)
    details = db.Column(db.JSON, nullable=True)

    admin_account = db.relationship(
        "Account",
        backref=db.backref("admin_audit_logs", lazy=True),
    )


class AdminBanner(BaseModel):
    __tablename__ = "admin_banners"

    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(1000), nullable=True)
    cta_label = db.Column(db.String(100), nullable=True)
    destination = db.Column(db.String(1000), nullable=True)
    placement = db.Column(
        db.String(50),
        nullable=False,
        default="HOME_HERO",
        index=True,
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    starts_at = db.Column(db.DateTime, nullable=True, index=True)
    ends_at = db.Column(db.DateTime, nullable=True, index=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False, index=True)


class PlatformSetting(BaseModel):
    __tablename__ = "platform_settings"

    key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    value = db.Column(db.JSON, nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False, index=True)
    description = db.Column(db.String(500), nullable=True)
