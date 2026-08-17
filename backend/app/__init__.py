import os
import threading
from flask import Flask, jsonify
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

    # 轻量级健康检查端点（不依赖数据库）
    @app.route("/api/health")
    def health_check():
        return jsonify({"status": "ok"})

    # 配置定时任务
    _configure_scheduler(app)

    # 确保数据库表已创建
    with app.app_context():
        db.create_all()

        # 后台线程自动种子：不阻塞启动
        _auto_seed_background(app)

    return app


def _auto_seed_background(app):
    """在后台线程中检查并填充种子数据，不阻塞服务启动"""
    def _seed_worker():
        with app.app_context():
            try:
                from app.models import Brand
                if Brand.query.count() == 0:
                    app.logger.info("数据库为空，开始后台填充种子数据...")
                    from seed_data import seed_brands, seed_data_sources, seed_mock_articles, seed_daily_summaries
                    seed_brands()
                    seed_data_sources()
                    seed_mock_articles(days=15)
                    seed_daily_summaries()
                    app.logger.info("种子数据填充完成")
            except Exception as e:
                app.logger.warning(f"自动种子数据失败（不影响启动）: {e}")

    t = threading.Thread(target=_seed_worker, daemon=True)
    t.start()


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
