import os
from datetime import timedelta


def _resolve_secret_key():
    """Flask SECRET_KEY: required in production, dev-only fallback otherwise."""
    key = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY")
    if key:
        return key
    if os.getenv("FLASK_ENV") == "production":
        raise RuntimeError(
            "SECRET_KEY must be set in production. Refusing to start with an insecure default."
        )
    return "dev-only-insecure-secret-key"


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:3001", "http://localhost:5000"]
    SECRET_KEY = _resolve_secret_key()

class DevelopmentConfig(Config):
    DEBUG = True
    # Echo can be re-enabled via SQLALCHEMY_ECHO=1, but defaults off so the
    # console isn't flooded with every SQL statement during development.
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") == "1"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///timetable.db")

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # The in-memory limiter is shared across every test in the process, so
    # rate limits from one test would bleed into the next. Disable in tests.
    RATELIMIT_ENABLED = False

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
