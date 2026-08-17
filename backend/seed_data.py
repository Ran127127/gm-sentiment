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


def seed_mock_articles_lightweight(days=7):
    """轻量级Mock文章生成 —— 不导入SnowNLP/jieba，使用预计算情感分数
    专为Render免费设计，避免NLP库导致OOM"""
    today = date.today()
    count = 0

    for day_offset in range(days):
        current_date = today - timedelta(days=day_offset)

        for brand_name, brand_info in BRAND_MODELS.items():
            article_count = random.randint(2, 4)

            for _ in range(article_count):
                model = random.choice(brand_info["models"])
                source_data = random.choice(DATA_SOURCES)
                source = DataSource.query.filter_by(name=source_data["name"]).first()
                brand = Brand.query.filter_by(name_cn=brand_name).first()
                car_model = CarModel.query.filter_by(
                    brand_id=brand.id, name_cn=model["name_cn"]
                ).first() if brand else None

                # 随机情感倾向
                sentiment_bias = random.choices(
                    ["positive", "negative", "neutral"],
                    weights=[0.5, 0.2, 0.3],
                )[0]

                article_data = generate_article(brand_name, model, source_data, sentiment_bias)
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

                # 预计算情感分数（不调用NLP）
                if sentiment_bias == "positive":
                    score = round(random.uniform(0.65, 0.95), 4)
                    label = "positive"
                elif sentiment_bias == "negative":
                    score = round(random.uniform(0.1, 0.35), 4)
                    label = "negative"
                else:
                    score = round(random.uniform(0.4, 0.6), 4)
                    label = "neutral"

                # 随机方面分数
                aspect_names = ["外观", "内饰", "动力", "空间", "性价比", "操控", "舒适性"]
                aspects = {}
                for asp in aspect_names:
                    if sentiment_bias == "positive":
                        aspects[asp] = round(random.uniform(0.5, 0.95), 2)
                    elif sentiment_bias == "negative":
                        aspects[asp] = round(random.uniform(0.1, 0.45), 2)
                    else:
                        aspects[asp] = round(random.uniform(0.35, 0.65), 2)

                # 随机关键词
                kw_pool = {
                    "positive": ["空间大", "油耗低", "性价比高", "配置丰富", "外观大气", "动力充沛", "隔音好"],
                    "negative": ["油耗高", "异响", "做工粗糙", "空间小", "起步肉", "刹车偏软", "噪音大"],
                    "neutral": ["表现均衡", "中规中矩", "够用", "尚可", "一般"],
                }
                keywords = random.sample(kw_pool[sentiment_bias], min(3, len(kw_pool[sentiment_bias])))

                sentiment = SentimentResult(
                    target_type="article",
                    target_id=article.id,
                    score=score,
                    label=label,
                    keywords=keywords,
                    aspects=aspects,
                    model_version="lightweight_v1",
                )
                db.session.add(sentiment)

                # 评论（同样使用预计算分数）
                for c_data in article_data.get("comments", []):
                    comment = Comment(
                        article_id=article.id,
                        content=c_data["content"],
                        author=c_data["author"],
                        like_count=c_data["like_count"],
                    )
                    db.session.add(comment)
                    db.session.flush()

                    # 评论情感分数基于文章倾向加随机偏移
                    c_score = max(0.01, min(0.99, score + random.uniform(-0.15, 0.15)))
                    c_score = round(c_score, 4)
                    if c_score > 0.6:
                        c_label = "positive"
                    elif c_score < 0.4:
                        c_label = "negative"
                    else:
                        c_label = "neutral"

                    c_sentiment = SentimentResult(
                        target_type="comment",
                        target_id=comment.id,
                        score=c_score,
                        label=c_label,
                        keywords=random.sample(keywords, min(2, len(keywords))),
                        aspects={},
                        model_version="lightweight_v1",
                    )
                    db.session.add(c_sentiment)

                count += 1

    db.session.commit()
    print(f"  [轻量级] 生成 {count} 篇文章及评论（无NLP）")
    return count


def seed_mock_articles(days=30):
    """生成Mock文章数据（完整版，使用SnowNLP情感分析）"""
    from sentiment.analyzer import ChineseSentimentAnalyzer
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
    """根据已有文章数据生成每日汇总（品牌级 + 车型级）"""
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

            # 车型级每日汇总
            models = CarModel.query.filter_by(brand_id=brand.id).all()
            for model in models:
                model_articles = [a for a in articles if a.model_id == model.id]
                if not model_articles:
                    continue

                model_aids = [a.id for a in model_articles]
                model_sentiments = [s for s in sentiments if s.target_id in model_aids]

                m_total = len(model_articles)
                m_positive = len([s for s in model_sentiments if s.label == "positive"])
                m_negative = len([s for s in model_sentiments if s.label == "negative"])
                m_neutral = len([s for s in model_sentiments if s.label == "neutral"])
                m_avg = (sum(s.score for s in model_sentiments) / len(model_sentiments)) if model_sentiments else 0.5

                m_kw_freq = {}
                for s in model_sentiments:
                    if s.keywords:
                        for kw in s.keywords:
                            m_kw_freq[kw] = m_kw_freq.get(kw, 0) + 1
                m_hot_keywords = [k for k, _ in sorted(m_kw_freq.items(), key=lambda x: -x[1])[:10]]

                model_summary = DailySummary(
                    date=current_date,
                    brand_id=brand.id,
                    model_id=model.id,
                    source_id=None,
                    total_count=m_total,
                    positive_count=m_positive,
                    negative_count=m_negative,
                    neutral_count=m_neutral,
                    avg_score=m_avg,
                    hot_keywords=m_hot_keywords,
                )
                db.session.add(model_summary)
                count += 1

    db.session.commit()
    print(f"  生成 {count} 条每日汇总（品牌+车型）")


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
