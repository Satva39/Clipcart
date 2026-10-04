import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _csv_env(name, default=""):
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class Config:
    """Single source of truth for backend runtime configuration."""

    ENV = os.getenv("FLASK_ENV", "development").strip().lower()
    DEBUG = ENV == "development"
    TESTING = ENV == "testing"

    SECRET_KEY = _required_env("SECRET_KEY")
    JWT_SECRET_KEY = _required_env("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=14)
    ADMIN_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    ADMIN_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    ADMIN_PASSWORD_RESET_TTL = int(os.getenv("ADMIN_PASSWORD_RESET_TTL", "900"))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    SQLALCHEMY_DATABASE_URI = _required_env("DATABASE_URL")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    _configured_cors_origins = _csv_env(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175,http://localhost:5176,http://127.0.0.1:5176",
    )
    _local_cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ]
    # Keep explicitly configured production origins, but always allow the local
    # Vite portals during development so a production .env does not break local
    # integration testing. Production uses only the configured list.
    CORS_ORIGINS = list(
        dict.fromkeys(
            _configured_cors_origins
            + (_local_cors_origins if ENV == "development" else [])
        )
    )

    CLIPCART_ADMIN_EMAIL = os.getenv("CLIPCART_ADMIN_EMAIL", "").strip().lower()
    CLIPCART_ADMIN_PORTAL_URL = (
        os.getenv(
            "CLIPCART_ADMIN_PORTAL_URL",
            "http://localhost:5176",
        )
        .strip()
        .rstrip("/")
    )

    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()

    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "").strip()
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "").strip()

    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
    FROM_EMAIL = os.getenv("FROM_EMAIL", "").strip()

    JSON_SORT_KEYS = False
