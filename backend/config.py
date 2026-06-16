import os
from datetime import timedelta


# Obvious placeholder values we refuse to boot with in production.
_WEAK_SECRETS = {
    "", "secret", "changeme", "change-me", "dev-only-insecure-secret-key",
    "your-secret-key", "please-change-me", "password",
}
_MIN_SECRET_LEN = 32


def _resolve_secret_key():
    """Flask SECRET_KEY: required (and strong) in production, dev fallback otherwise.

    In production we refuse to start unless the key is set, long enough, and not
    an obvious placeholder — a weak/guessable key lets anyone forge login
    sessions for any school.
    """
    key = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY")
    is_prod = os.getenv("FLASK_ENV") == "production"
    if is_prod:
        if not key or key.strip().lower() in _WEAK_SECRETS or len(key) < _MIN_SECRET_LEN:
            raise RuntimeError(
                "SECRET_KEY (and JWT_SECRET_KEY) must be set in production to a strong, "
                f"random value of at least {_MIN_SECRET_LEN} characters. Generate one with: "
                "python3 -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return key
    return key or "dev-only-insecure-secret-key"


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

def _normalize_db_url(url):
    # Some hosts (Render, Heroku, ...) hand out "postgres://", which SQLAlchemy
    # 1.4+ no longer accepts; psycopg2 wants "postgresql://".
    if url and url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.getenv("DATABASE_URL"))

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
