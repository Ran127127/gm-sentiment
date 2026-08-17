from datetime import date, timedelta
from flask import request
from sqlalchemy import func, case, and_
from app.api import api_bp
from app.extensions import db
from app.models import Brand, CarModel, Article, SentimentResult, DailySummary, DataSource
from app.utils.response import success_response


@api_bp.route("/dashboard/overview", methods=["GET"])
def dashboard_overview():
    """全局概览：三大品牌舆情摘要卡片"""
    brands = Brand.query.all()
    result = []
    today = date.today()
    week_ago = today - timedelta(days=7)

    for brand in brands:
        # 近7天数据统计
        summaries = DailySummary.query.filter(
            DailySummary.brand_id == brand.id,
            DailySummary.date >= week_ago,
            DailySummary.model_id.is_(None),
            DailySummary.source_id.is_(None),
        ).all()

        total = sum(s.total_count for s in summaries)
        positive = sum(s.positive_count for s in summaries)
        negative = sum(s.negative_count for s in summaries)
        neutral = sum(s.neutral_count for s in summaries)
        avg_score = (sum(s.avg_score * s.total_count for s in summaries if s.avg_score)
                     / total) if total > 0 else 0.5

        # 舆情指数 = avg_score * 100
        sentiment_index = round(avg_score * 100)

        # 较昨日变化
        yesterday_summary = DailySummary.query.filter(
            DailySummary.brand_id == brand.id,
            DailySummary.date == today - timedelta(days=1),
            DailySummary.model_id.is_(None),
            DailySummary.source_id.is_(None),
        ).first()
        day_before = DailySummary.query.filter(
            DailySummary.brand_id == brand.id,
            DailySummary.date == today - timedelta(days=2),
            DailySummary.model_id.is_(None),
            DailySummary.source_id.is_(None),
        ).first()

        prev_index = round((day_before.avg_score or 0.5) * 100) if day_before else sentiment_index
        change = sentiment_index - prev_index

        result.append({
            "brand": brand.to_dict(),
            "sentiment_index": sentiment_index,
            "change": change,
            "total_count": total,
            "positive_ratio": round(positive / total * 100, 1) if total > 0 else 0,
            "negative_ratio": round(negative / total * 100, 1) if total > 0 else 0,
            "neutral_ratio": round(neutral / total * 100, 1) if total > 0 else 0,
        })

    return success_response(result)


@api_bp.route("/dashboard/sentiment-trend", methods=["GET"])
def sentiment_trend():
    """情感趋势折线图"""
    brand_id = request.args.get("brand_id", type=int)
    days = request.args.get("days", 7, type=int)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    query = DailySummary.query.filter(
        DailySummary.date >= start_date,
        DailySummary.date <= end_date,
        DailySummary.model_id.is_(None),
        DailySummary.source_id.is_(None),
    )
    if brand_id:
        query = query.filter(DailySummary.brand_id == brand_id)

    summaries = query.order_by(DailySummary.date).all()

    # 按日期聚合
    date_map = {}
    for s in summaries:
        d = s.date.isoformat()
        if d not in date_map:
            date_map[d] = {"date": d, "positive": 0, "negative": 0, "neutral": 0, "total": 0}
        date_map[d]["positive"] += s.positive_count
        date_map[d]["negative"] += s.negative_count
        date_map[d]["neutral"] += s.neutral_count
        date_map[d]["total"] += s.total_count

    trend = sorted(date_map.values(), key=lambda x: x["date"])
    return success_response(trend)


@api_bp.route("/dashboard/source-distribution", methods=["GET"])
def source_distribution():
    """各平台数据量分布"""
    brand_id = request.args.get("brand_id", type=int)

    query = db.session.query(
        DataSource.display_name,
        func.count(Article.id),
    ).join(Article, Article.source_id == DataSource.id)

    if brand_id:
        query = query.filter(Article.brand_id == brand_id)

    results = query.group_by(DataSource.id).all()
    data = [{"source": name, "count": count} for name, count in results]
    return success_response(data)


@api_bp.route("/dashboard/keyword-cloud", methods=["GET"])
def keyword_cloud():
    """关键词词云数据"""
    brand_id = request.args.get("brand_id", type=int)
    days = request.args.get("days", 7, type=int)
    start_date = date.today() - timedelta(days=days)

    query = db.session.query(
        SentimentResult.keywords,
    ).join(Article, and_(
        SentimentResult.target_type == "article",
        SentimentResult.target_id == Article.id,
    )).filter(Article.publish_time >= start_date.isoformat())

    if brand_id:
        query = query.filter(Article.brand_id == brand_id)

    results = query.all()
    word_freq = {}
    for (keywords,) in results:
        if keywords:
            for kw in keywords:
                word_freq[kw] = word_freq.get(kw, 0) + 1

    data = [{"name": k, "value": v} for k, v in
            sorted(word_freq.items(), key=lambda x: -x[1])[:50]]
    return success_response(data)


@api_bp.route("/dashboard/model-comparison", methods=["GET"])
def model_comparison():
    """车型对比雷达图（维度情感分析）"""
    brand_id = request.args.get("brand_id", type=int)
    if not brand_id:
        return success_response([])

    models = CarModel.query.filter_by(brand_id=brand_id, is_new=True).all()
    aspects_list = ["外观", "内饰", "动力", "空间", "性价比", "操控", "舒适性"]
    result = []

    for model in models:
        # 查询该车型所有情感分析结果的维度评分
        sentiments = SentimentResult.query.filter(
            SentimentResult.target_type == "article",
            SentimentResult.target_id.in_(
                db.session.query(Article.id).filter_by(model_id=model.id)
            ),
            SentimentResult.aspects.isnot(None),
        ).all()

        aspect_scores = {}
        for s in sentiments:
            if s.aspects:
                for aspect, score in s.aspects.items():
                    if aspect not in aspect_scores:
                        aspect_scores[aspect] = []
                    aspect_scores[aspect].append(score)

        radar_data = {}
        for aspect in aspects_list:
            scores = aspect_scores.get(aspect, [])
            radar_data[aspect] = round(sum(scores) / len(scores) * 100, 1) if scores else 50

        result.append({
            "model": model.to_dict(),
            "radar": radar_data,
            "article_count": Article.query.filter_by(model_id=model.id).count(),
        })

    return success_response(result)


@api_bp.route("/dashboard/hot-articles", methods=["GET"])
def hot_articles():
    """热门文章列表"""
    brand_id = request.args.get("brand_id", type=int)
    limit = request.args.get("limit", 10, type=int)

    query = Article.query
    if brand_id:
        query = query.filter_by(brand_id=brand_id)

    articles = query.order_by(
        (Article.like_count + Article.comment_count + Article.share_count).desc()
    ).limit(limit).all()

    return success_response([a.to_dict() for a in articles])
