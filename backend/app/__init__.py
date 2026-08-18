import os
from flask import Flask
from app.config import config_map
from app.extensions import db, migrate, jwt, cors, scheduler


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # 注册蓝图
    from app.api import api_bp
    app.register_blueprint(api_bp)

    # 配置定时任务
    _configure_scheduler(app)

    # 确保数据库表已创建（开发环境）
    with app.app_context():
        db.create_all()
        # Render免费层无持久磁盘，服务休眠唤醒后SQLite丢失，自动补充种子数据
        _auto_seed_if_empty(app)

    return app


def _auto_seed_if_empty(app):
    """检测数据库为空时自动填充种子数据（应对Render免费层磁盘不持久）"""
    try:
        from app.models import Brand
        if Brand.query.count() == 0:
            print("[auto-seed] 数据库为空，自动填充种子数据...")
            from seed_data import seed_brands, seed_data_sources, seed_mock_articles_lightweight, seed_daily_summaries
            seed_brands()
            seed_data_sources()
            seed_mock_articles_lightweight(days=7)
            seed_daily_summaries()
            print("[auto-seed] 种子数据填充完成")
    except Exception as e:
        print(f"[auto-seed] 自动填充失败: {e}")


def _configure_scheduler(app):
    """配置定时抓取任务"""
    app.config["SCHEDULER_API_ENABLED"] = False

    # 定时任务定义
    jobs = [
        {
            "id": "scrape_autohome",
            "func": "scraper.pipeline:ScrapingPipeline.run_source",
            "args": ("autohome",),
            "trigger": "cron",
            "hour": "8,20",
            "minute": "0",
        },
        {
            "id": "scrape_dongchedi",
            "func": "scraper.pipeline:ScrapingPipeline.run_source",
            "args": ("dongchedi",),
            "trigger": "cron",
            "hour": "9,21",
            "minute": "0",
        },
        {
            "id": "scrape_yiche",
            "func": "scraper.pipeline:ScrapingPipeline.run_source",
            "args": ("yiche",),
            "trigger": "cron",
            "hour": "10",
            "minute": "0",
        },
        {
            "id": "generate_recommendations",
            "func": "sentiment.recommender:RecommendationEngine.generate_all",
            "trigger": "cron",
            "hour": "22",
            "minute": "0",
        },
    ]

    for job in jobs:
        scheduler.add_job(
            id=job["id"],
            func=job["func"],
            args=job.get("args", ()),
            trigger=job["trigger"],
            **{k: v for k, v in job.items()
               if k not in ("id", "func", "args", "trigger")},
        )

    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
