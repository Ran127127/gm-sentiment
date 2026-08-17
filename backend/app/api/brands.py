from flask import request
from app.api import api_bp
from app.extensions import db
from app.models import Brand, CarModel, DailySummary, SentimentResult, Article
from app.utils.response import success_response, error_response


@api_bp.route("/brands", methods=["GET"])
def list_brands():
    brands = Brand.query.all()
    return success_response([b.to_dict() for b in brands])


@api_bp.route("/brands/<int:brand_id>", methods=["GET"])
def get_brand(brand_id):
    brand = Brand.query.get_or_404(brand_id)
    return success_response(brand.to_dict())


@api_bp.route("/brands/<int:brand_id>/models", methods=["GET"])
def list_models(brand_id):
    Brand.query.get_or_404(brand_id)
    models = CarModel.query.filter_by(brand_id=brand_id).all()
    return success_response([m.to_dict() for m in models])


@api_bp.route("/brands/<int:brand_id>/summary", methods=["GET"])
def brand_summary(brand_id):
    """品牌舆情详细摘要"""
    from datetime import date, timedelta
    Brand.query.get_or_404(brand_id)

    days = request.args.get("days", 30, type=int)
    start = date.today() - timedelta(days=days)

    summaries = DailySummary.query.filter(
        DailySummary.brand_id == brand_id,
        DailySummary.date >= start,
        DailySummary.model_id.is_(None),
        DailySummary.source_id.is_(None),
    ).all()

    total = sum(s.total_count for s in summaries)
    positive = sum(s.positive_count for s in summaries)
    negative = sum(s.negative_count for s in summaries)
    neutral = sum(s.neutral_count for s in summaries)
    avg_score = (sum(s.avg_score * s.total_count for s in summaries if s.avg_score)
                 / total) if total > 0 else 0.5

    # 聚合热门关键词
    kw_freq = {}
    for s in summaries:
        if s.hot_keywords:
            for kw in s.hot_keywords:
                kw_freq[kw] = kw_freq.get(kw, 0) + 1
    hot_keywords = sorted(kw_freq.items(), key=lambda x: -x[1])[:20]

    return success_response({
        "total_count": total,
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": neutral,
        "avg_score": round(avg_score, 4),
        "hot_keywords": [{"name": k, "value": v} for k, v in hot_keywords],
    })


@api_bp.route("/models/<int:model_id>", methods=["GET"])
def model_detail(model_id):
    """车型详情：品牌信息 + 舆情汇总 + 维度分析 + 热门文章"""
    model = CarModel.query.get_or_404(model_id)
    brand = Brand.query.get_or_404(model.brand_id)

    # 车型级每日汇总
    summaries = DailySummary.query.filter_by(
        model_id=model.id
    ).all()

    total = sum(s.total_count for s in summaries)
    positive = sum(s.positive_count for s in summaries)
    negative = sum(s.negative_count for s in summaries)
    neutral = sum(s.neutral_count for s in summaries)
    avg_score = (sum(s.avg_score * s.total_count for s in summaries if s.avg_score)
                 / total) if total > 0 else 0.5

    # 热门关键词
    kw_freq = {}
    for s in summaries:
        if s.hot_keywords:
            for kw in s.hot_keywords:
                kw_freq[kw] = kw_freq.get(kw, 0) + 1
    hot_keywords = sorted(kw_freq.items(), key=lambda x: -x[1])[:15]

    # 维度情感分析 —— 从该车型文章的SentimentResult聚合
    article_ids = [a.id for a in model.articles]
    sentiments = []
    if article_ids:
        sentiments = SentimentResult.query.filter(
            SentimentResult.target_type == "article",
            SentimentResult.target_id.in_(article_ids),
        ).all()

    # 聚合方面分数
    aspect_scores = {}
    aspect_counts = {}
    for s in sentiments:
        if s.aspects:
            for asp, score in s.aspects.items():
                aspect_scores[asp] = aspect_scores.get(asp, 0) + score
                aspect_counts[asp] = aspect_counts.get(asp, 0) + 1
    aspects = []
    for asp in aspect_scores:
        avg = aspect_scores[asp] / aspect_counts[asp] if aspect_counts[asp] else 0
        aspects.append({"aspect": asp, "avg_score": round(avg, 4)})
    aspects.sort(key=lambda x: -x["avg_score"])

    # 热门文章
    top_articles = model.articles.order_by(
        Article.view_count.desc()
    ).limit(10).all()

    articles_data = []
    for a in top_articles:
        sent = next((s for s in sentiments if s.target_id == a.id), None)
        articles_data.append({
            "id": a.id,
            "title": a.title,
            "url": a.url,
            "source_name": a.source.display_name if a.source else "",
            "model_name": model.name_cn,
            "publish_time": a.publish_time.isoformat() if a.publish_time else None,
            "view_count": a.view_count or 0,
            "like_count": a.like_count or 0,
            "comment_count": a.comment_count or 0,
            "sentiment": sent.to_dict() if sent else None,
        })

    return success_response({
        "model": model.to_dict(),
        "brand": brand.to_dict(),
        "summary": {
            "total_count": total,
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "avg_score": round(avg_score, 4),
            "hot_keywords": [{"name": k, "value": v} for k, v in hot_keywords],
        },
        "aspects": aspects,
        "articles": articles_data,
    })
