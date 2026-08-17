from flask import request
from app.api import api_bp
from app.models import Article, Comment, SentimentResult
from app.utils.response import success_response, paginated_response
from app.extensions import db


@api_bp.route("/sentiment/articles", methods=["GET"])
def list_articles():
    """文章列表（带情感标签筛选）"""
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 20, type=int)
    brand_id = request.args.get("brand_id", type=int)
    model_id = request.args.get("model_id", type=int)
    label = request.args.get("label")  # positive/negative/neutral
    source_id = request.args.get("source_id", type=int)

    query = Article.query
    if brand_id:
        query = query.filter_by(brand_id=brand_id)
    if model_id:
        query = query.filter_by(model_id=model_id)
    if source_id:
        query = query.filter_by(source_id=source_id)
    if label:
        query = query.join(SentimentResult).filter(
            SentimentResult.target_type == "article",
            SentimentResult.label == label,
        )

    total = query.count()
    articles = query.order_by(Article.publish_time.desc()).offset(
        (page - 1) * size
    ).limit(size).all()

    return paginated_response(
        [a.to_dict() for a in articles], total, page, size
    )


@api_bp.route("/sentiment/articles/<int:article_id>", methods=["GET"])
def get_article(article_id):
    """文章详情（含评论和情感分析）"""
    article = Article.query.get_or_404(article_id)
    data = article.to_dict(include_content=True)
    comments = article.comments.order_by(Comment.like_count.desc()).limit(50).all()
    data["comments"] = [c.to_dict() for c in comments]
    return success_response(data)


@api_bp.route("/sentiment/aspect-analysis", methods=["GET"])
def aspect_analysis():
    """维度情感分析（外观/内饰/动力/空间/性价比等）"""
    brand_id = request.args.get("brand_id", type=int)
    model_id = request.args.get("model_id", type=int)

    query = SentimentResult.query.filter(
        SentimentResult.target_type == "article",
        SentimentResult.aspects.isnot(None),
    )

    if model_id:
        query = query.filter(
            SentimentResult.target_id.in_(
                db.session.query(Article.id).filter_by(model_id=model_id)
            )
        )
    elif brand_id:
        query = query.filter(
            SentimentResult.target_id.in_(
                db.session.query(Article.id).filter_by(brand_id=brand_id)
            )
        )

    results = query.all()
    aspect_scores = {}
    for s in results:
        if s.aspects:
            for aspect, score in s.aspects.items():
                if aspect not in aspect_scores:
                    aspect_scores[aspect] = []
                aspect_scores[aspect].append(score)

    data = []
    for aspect, scores in aspect_scores.items():
        data.append({
            "aspect": aspect,
            "avg_score": round(sum(scores) / len(scores), 4),
            "sample_count": len(scores),
            "positive_ratio": round(len([s for s in scores if s > 0.6]) / len(scores) * 100, 1),
            "negative_ratio": round(len([s for s in scores if s < 0.4]) / len(scores) * 100, 1),
        })

    data.sort(key=lambda x: x["avg_score"], reverse=True)
    return success_response(data)
