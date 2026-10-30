import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://myjo:myjo@127.0.0.1:3306/myjo_portal?charset=utf8mb4")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    TOKEN_HOURS = int(os.environ.get("TOKEN_HOURS", "8"))
    TIMEZONE = os.environ.get("APP_TIMEZONE", "Asia/Kolkata")
    MAX_LOGIN_ATTEMPTS = 5
    LOCK_MINUTES = 5
    # Outgoing messages. Leave empty to only log notifications (status "Logged").
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "Myjo Publications <no-reply@myjo.in>")
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")          # Meta WhatsApp Cloud API token
    WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
    SEND_MESSAGES = os.environ.get("SEND_MESSAGES", "0") == "1"


class TestConfig(Config):
    TESTING = True
    PASSWORD_ITERATIONS = 1000
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    SQLALCHEMY_ENGINE_OPTIONS = {}
