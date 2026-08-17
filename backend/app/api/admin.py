from flask import request
from flask_jwt_extended import jwt_required
from app.api import api_bp
from app.extensions import db
from app.models import Article, Comment, DataSource, SentimentResult
from app.utils.response import success_response, error_response


@api_bp.route("/admin/scraping-status", methods=["GET"])
@jwt_required()
def scraping_status():
    """数据抓取状态"""
    sources = DataSource.query.all()
    result = []
    for src in sources:
        latest_article = Article.query.filter_by(source_id=src.id).order_by(
            Article.scraped_at.desc()
        ).first()
        total = Article.query.filter_by(source_id=src.id).count()
        result.append({
            "source": src.to_dict(),
            "total_articles": total,
            "last_scraped": latest_article.scraped_at.isoformat() if latest_article else None,
        })
    return success_response(result)


@api_bp.route("/admin/scraping/trigger", methods=["POST"])
@jwt_required()
def trigger_scraping():
    """手动触发数据抓取"""
    source_id = request.args.get("source_id", type=int)
    if not source_id:
        return error_response("请指定source_id")

    from scraper.pipeline import ScrapingPipeline
    pipeline = ScrapingPipeline()
    try:
        count = pipeline.run_source_by_id(source_id)
        return success_response({"items_scraped": count})
    except Exception as e:
        return error_response(f"抓取失败: {str(e)}", 500)


@api_bp.route("/admin/system-stats", methods=["GET"])
@jwt_required()
def system_stats():
    """系统统计"""
    return success_response({
        "total_articles": Article.query.count(),
        "total_comments": Comment.query.count(),
        "total_sentiment_analyzed": SentimentResult.query.count(),
        "data_sources": DataSource.query.count(),
    })
