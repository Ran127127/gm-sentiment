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

    return app


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
