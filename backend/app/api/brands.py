from flask import request
from app.api import api_bp
from app.models import Brand, CarModel, DailySummary
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
