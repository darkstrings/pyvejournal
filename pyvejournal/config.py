import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _database_url():
    url = os.environ.get("DATABASE_URL") or os.environ.get("PYVEJOURNAL_DATABASE_URL")
    if not url:
        (BASE_DIR / "instance").mkdir(exist_ok=True)
        return f"sqlite:///{BASE_DIR / 'instance' / 'site.db'}"
    # Render/Heroku hand out "postgres://", SQLAlchemy wants an explicit driver.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("PYVEJOURNAL_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Uploads (userpics) are small; reject anything bigger before it reaches Python.
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024

    # Cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # Email (password resets)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME") or os.environ.get("PYVEJOURNAL_EMAIL_USER")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or os.environ.get("PYVEJOURNAL_EMAIL_PASS")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME

    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True

    ENTRIES_PER_PAGE = 10
    DEMO_ENABLED = os.environ.get("DEMO_ENABLED", "1") == "1"


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


class DevelopmentConfig(Config):
    SECRET_KEY = Config.SECRET_KEY or "dev-only-not-secret"


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    SERVER_NAME = "localhost"
    BCRYPT_LOG_ROUNDS = 4


def pick_config():
    env = os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV")
    if env == "production" or os.environ.get("RENDER"):
        return ProductionConfig
    return DevelopmentConfig
