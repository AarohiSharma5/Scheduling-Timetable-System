import os
from datetime import timedelta

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:3001", "http://localhost:5000"]
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

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

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
