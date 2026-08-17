import os
import sys
import traceback
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

    # 健康检查端点 —— 必须最先注册，确保快速响应
    @app.route("/api/health")
    def health_check():
        return jsonify({"status": "ok", "config": config_name})

    # 注册蓝图
    try:
        from app.api import api_bp
        app.register_blueprint(api_bp)
    except Exception as e:
        print(f"[ERROR] Failed to register blueprints: {e}", file=sys.stderr)
        traceback.print_exc()

    # 数据库初始化（含schema迁移检查）
    try:
        with app.app_context():
            _check_and_migrate_schema()
    except Exception as e:
        print(f"[ERROR] DB init failed: {e}", file=sys.stderr)
        traceback.print_exc()

    # 调度器（仅开发环境启用）
    if config_name == "development":
        try:
            _configure_scheduler(app)
        except Exception as e:
            print(f"[WARN] Scheduler failed: {e}", file=sys.stderr)

    return app


def _check_and_migrate_schema():
    """检查SQLite schema是否正确，若BigInteger列存在则重建表"""
    from sqlalchemy import text, inspect

    engine = db.engine
    inspector = inspect(engine)

    # 检查articles表是否存在且id列类型是否正确
    needs_rebuild = False
    if inspector.has_table("articles"):
        columns = {col["name"]: col for col in inspector.get_columns("articles")}
        id_col = columns.get("id")
        if id_col:
            col_type = str(id_col["type"]).upper()
            # SQLite autoincrement需要INTEGER，不是BIGINT
            if "BIGINT" in col_type or "BIG" in col_type:
                needs_rebuild = True
                print(f"[SCHEMA] articles.id is {col_type}, needs INTEGER. Rebuilding...", file=sys.stderr)

    if needs_rebuild:
        print("[SCHEMA] Dropping and recreating all tables...", file=sys.stderr)
        db.drop_all()
        db.create_all()
        print("[SCHEMA] Schema rebuilt successfully!", file=sys.stderr)
    else:
        db.create_all()


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
