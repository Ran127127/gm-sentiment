import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_db_url(url: str) -> str:
    """
    标准化数据库URL。
    Render提供的DATABASE_URL可能以 postgres:// 开头，
    SQLAlchemy >= 1.4 需要 postgresql:// 前缀。
    """
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "gm-sentiment-dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False  # 支持中文JSON响应

    # JWT配置
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "gm-jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24小时

    # 调度器配置
    SCHEDULER_API_ENABLED = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # 开发环境使用SQLite
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///gm_sentiment.db"
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    # Render提供PostgreSQL，通过DATABASE_URL环境变量传入
    # 本地部署默认MySQL
    _raw_url = os.getenv("DATABASE_URL", "")
    if _raw_url and ("postgres" in _raw_url or "psycopg2" in _raw_url):
        # Render PostgreSQL
        SQLALCHEMY_DATABASE_URI = _normalize_db_url(_raw_url)
    else:
        # 本地MySQL或默认
        SQLALCHEMY_DATABASE_URI = _raw_url or (
            "mysql+pymysql://gm_app:password@localhost/gm_sentiment?charset=utf8mb4"
        )


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
