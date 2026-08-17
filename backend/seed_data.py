"""
初始化种子数据 —— 品牌、车型、数据源、Mock文章数据
"""
import sys
import os
import random
from datetime import date, timedelta, datetime

# 确保项目根目录在Python路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Brand, CarModel, DataSource, Article, Comment, SentimentResult, DailySummary
from scraper.mock_generator import BRAND_MODELS, DATA_SOURCES, generate_article
from sentiment.analyzer import ChineseSentimentAnalyzer


def seed_brands():
    """初始化品牌和车型"""
    for brand_name, brand_info in BRAND_MODELS.items():
        brand = Brand.query.filter_by(name_cn=brand_name).first()
        if not brand:
            brand = Brand(
                name_cn=brand_name,
                name_en=brand_name,  # 简化处理
            )
            db.session.add(brand)
            db.session.flush()
            print(f"  创建品牌: {brand_name} (ID={brand.id})")

            for model_data in brand_info["models"]:
                model = CarModel(
                    brand_id=brand.id,
                    name_cn=model_data["name_cn"],
                    name_en=model_data.get("name_en", ""),
                    category=model_data.get("category"),
                    is_new=True,
                )
                db.session.add(model)
                print(f"    创建车型: {model_data['name_cn']}")

    db.session.commit()


def seed_data_sources():
    """初始化数据源"""
    for src_data in DATA_SOURCES:
        source = DataSource.query.filter_by(name=src_data["name"]).first()
        if not source:
            source = DataSource(**src_data)
            db.session.add(source)
            print(f"  创建数据源: {src_data['display_name']}")

    db.session.commit()


def seed_mock_articles(days=30):
    """生成Mock文章数据"""
    analyzer = ChineseSentimentAnalyzer()
    today = date.today()
    count = 0

    for day_offset in range(days):
        current_date = today - timedelta(days=day_offset)

        for brand_name, brand_info in BRAND_MODELS.items():
            article_count = random.randint(2, 5)

            for _ in range(article_count):
                model = random.choice(brand_info["models"])
                source_data = random.choice(DATA_SOURCES)
                source = DataSource.query.filter_by(name=source_data["name"]).first()
                brand = Brand.query.filter_by(name_cn=brand_name).first()
                car_model = CarModel.query.filter_by(
                    brand_id=brand.id, name_cn=model["name_cn"]
                ).first() if brand else None

                article_data = generate_article(brand_name, model, source_data)
                article_data["publish_time"] = datetime.combine(
                    current_date,
                    datetime.min.time().replace(
                        hour=random.randint(6, 23),
                        minute=random.randint(0, 59),
                    )
                )

                # 检查去重
                existing = Article.query.filter_by(
                    source_id=source.id, url=article_data["url"]
                ).first()
                if existing:
                    continue

                article = Article(
                    source_id=source.id,
                    brand_id=brand.id if brand else None,
                    model_id=car_model.id if car_model else None,
                    title=article_data["title"],
                    content=article_data["content"],
                    summary=article_data["summary"],
                    url=article_data["url"],
                    author=article_data["author"],
                    publish_time=article_data["publish_time"],
                    view_count=article_data["view_count"],
                    like_count=article_data["like_count"],
                    comment_count=article_data["comment_count"],
                    share_count=article_data["share_count"],
                )
                db.session.add(article)
                db.session.flush()

                # 文章情感分析
                text = f"{article.title}。{article.content}"
                result = analyzer.analyze(text)
                sentiment = SentimentResult(
                    target_type="article",
                    target_id=article.id,
                    score=result["score"],
                    label=result["label"],
                    keywords=result["keywords"],
                    aspects=result["aspects"],
                )
                db.session.add(sentiment)

                # 保存评论
                for c_data in article_data.get("comments", []):
                    comment = Comment(
                        article_id=article.id,
                        content=c_data["content"],
                        author=c_data["author"],
                        like_count=c_data["like_count"],
                    )
                    db.session.add(comment)
                    db.session.flush()

                    c_result = analyzer.analyze(c_data["content"])
                    c_sentiment = SentimentResult(
                        target_type="comment",
                        target_id=comment.id,
                        score=c_result["score"],
                        label=c_result["label"],
                        keywords=c_result["keywords"],
                        aspects=c_result["aspects"],
                    )
                    db.session.add(c_sentiment)

                count += 1

    db.session.commit()
    print(f"  生成 {count} 篇Mock文章及评论")
    return count


def seed_daily_summaries():
    """根据已有文章数据生成每日汇总"""
    today = date.today()
    brands = Brand.query.all()
    sources = DataSource.query.all()
    count = 0

    for day_offset in range(30):
        current_date = today - timedelta(days=day_offset)
        date_str = current_date.isoformat()
        next_date_str = (current_date + timedelta(days=1)).isoformat()

        for brand in brands:
            # 品牌+日期汇总
            articles = Article.query.filter(
                Article.brand_id == brand.id,
                Article.publish_time >= date_str,
                Article.publish_time < next_date_str,
            ).all()

            if not articles:
                continue

            article_ids = [a.id for a in articles]
            sentiments = SentimentResult.query.filter(
                SentimentResult.target_type == "article",
                SentimentResult.target_id.in_(article_ids),
            ).all()

            total = len(articles)
            positive = len([s for s in sentiments if s.label == "positive"])
            negative = len([s for s in sentiments if s.label == "negative"])
            neutral = len([s for s in sentiments if s.label == "neutral"])
            avg_score = (sum(s.score for s in sentiments) / len(sentiments)) if sentiments else 0.5

            # 热门关键词
            kw_freq = {}
            for s in sentiments:
                if s.keywords:
                    for kw in s.keywords:
                        kw_freq[kw] = kw_freq.get(kw, 0) + 1
            hot_keywords = [k for k, _ in sorted(kw_freq.items(), key=lambda x: -x[1])[:10]]

            summary = DailySummary(
                date=current_date,
                brand_id=brand.id,
                model_id=None,
                source_id=None,
                total_count=total,
                positive_count=positive,
                negative_count=negative,
                neutral_count=neutral,
                avg_score=avg_score,
                hot_keywords=hot_keywords,
            )
            db.session.add(summary)
            count += 1

    db.session.commit()
    print(f"  生成 {count} 条每日汇总")


def run_seed():
    """执行全部种子数据初始化"""
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("开始初始化种子数据...")
        print("=" * 50)

        print("\n[1/4] 初始化品牌与车型...")
        seed_brands()

        print("\n[2/4] 初始化数据源...")
        seed_data_sources()

        print("\n[3/4] 生成Mock文章数据（约30天）...")
        seed_mock_articles(days=30)

        print("\n[4/4] 生成每日汇总统计...")
        seed_daily_summaries()

        # 生成推荐建议
        print("\n[5/5] 生成智能建议...")
        from sentiment.recommender import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.generate_all()
        print(f"  生成 {len(recs)} 条建议")

        print("\n" + "=" * 50)
        print("种子数据初始化完成！")
        print(f"  品牌: {Brand.query.count()}")
        print(f"  车型: {CarModel.query.count()}")
        print(f"  数据源: {DataSource.query.count()}")
        print(f"  文章: {Article.query.count()}")
        print(f"  评论: {Comment.query.count()}")
        print(f"  情感分析: {SentimentResult.query.count()}")
        print(f"  每日汇总: {DailySummary.query.count()}")
        print("=" * 50)


if __name__ == "__main__":
    run_seed()
