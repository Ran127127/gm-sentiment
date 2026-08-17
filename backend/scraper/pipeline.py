"""
数据抓取管道 —— 协调各数据源的抓取任务
支持真实抓取器和Mock数据两种模式
"""
import logging
from datetime import datetime
from app.extensions import db
from app.models import Article, Comment, DataSource, SentimentResult, DailySummary
from sentiment.analyzer import ChineseSentimentAnalyzer

logger = logging.getLogger(__name__)


class BaseScraper:
    """抓取器基类"""
    source_name = None

    def scrape(self, **kwargs) -> list:
        """执行抓取，返回文章数据列表"""
        raise NotImplementedError


class AutohomeScraper(BaseScraper):
    """汽车之家抓取器 —— 委托给独立模块"""
    source_name = "autohome"

    def scrape(self, **kwargs):
        from scraper.autohome import AutohomeScraper as _RealScraper
        scraper = _RealScraper()
        try:
            return scraper.scrape(**kwargs)
        except Exception as e:
            logger.error(f"[autohome] 抓取异常: {e}")
            return []
        finally:
            scraper.close()


class DongchediScraper(BaseScraper):
    """懂车帝抓取器 —— 委托给独立模块"""
    source_name = "dongchedi"

    def scrape(self, **kwargs):
        from scraper.dongchedi import DongchediScraper as _RealScraper
        scraper = _RealScraper()
        try:
            return scraper.scrape(**kwargs)
        except Exception as e:
            logger.error(f"[dongchedi] 抓取异常: {e}")
            return []
        finally:
            scraper.close()


class YicheScraper(BaseScraper):
    """易车抓取器 —— 委托给独立模块"""
    source_name = "yiche"

    def scrape(self, **kwargs):
        from scraper.yiche import YicheScraper as _RealScraper
        scraper = _RealScraper()
        try:
            return scraper.scrape(**kwargs)
        except Exception as e:
            logger.error(f"[yiche] 抓取异常: {e}")
            return []
        finally:
            scraper.close()


class ScrapingPipeline:
    """抓取管道编排器"""

    SCRAPERS = {
        "autohome": AutohomeScraper,
        "dongchedi": DongchediScraper,
        "yiche": YicheScraper,
    }

    def __init__(self):
        self.analyzer = ChineseSentimentAnalyzer()

    def run_source(self, source_name: str, use_mock: bool = False, **kwargs) -> int:
        """
        运行指定数据源的抓取任务。
        use_mock=True 时使用Mock数据（开发/演示用）。
        """
        source = DataSource.query.filter_by(name=source_name).first()
        if not source:
            raise ValueError(f"数据源未注册: {source_name}")

        if use_mock:
            articles_data = self._generate_mock(source_name, **kwargs)
        else:
            if source_name not in self.SCRAPERS:
                raise ValueError(f"未知的数据源: {source_name}")
            scraper = self.SCRAPERS[source_name]()
            articles_data = scraper.scrape(**kwargs)

            # 如果真实抓取器返回空数据，自动降级到Mock
            if not articles_data:
                logger.warning(
                    f"[{source_name}] 真实抓取返回空数据，降级到Mock模式"
                )
                articles_data = self._generate_mock(source_name, **kwargs)

        count = 0
        for data in articles_data:
            article = self._save_article(source, data)
            if article:
                self._analyze_and_save(article, data)
                count += 1

        db.session.commit()
        logger.info(f"[{source_name}] 抓取完成，新增 {count} 篇文章")
        return count

    def run_source_by_id(self, source_id: int, **kwargs) -> int:
        source = DataSource.query.get(source_id)
        if not source:
            raise ValueError(f"数据源ID不存在: {source_id}")
        return self.run_source(source.name, **kwargs)

    def run_all(self, use_mock: bool = False, **kwargs) -> dict:
        """运行所有数据源"""
        results = {}
        for name in self.SCRAPERS:
            try:
                count = self.run_source(name, use_mock=use_mock, **kwargs)
                results[name] = {"status": "success", "count": count}
            except Exception as e:
                results[name] = {"status": "failed", "error": str(e)}
                logger.error(f"[{name}] 抓取失败: {e}")
        return results

    def _generate_mock(self, source_name: str, **kwargs) -> list:
        """生成Mock数据作为降级方案"""
        from scraper.mock_generator import (
            BRAND_MODELS, DATA_SOURCES, generate_article,
        )
        import random
        from datetime import timedelta

        source_info = None
        for s in DATA_SOURCES:
            if s["name"] == source_name:
                source_info = s
                break
        if not source_info:
            return []

        articles = []
        count = kwargs.get("max_articles", 15)

        for brand_name, brand_info in BRAND_MODELS.items():
            for _ in range(count // len(BRAND_MODELS)):
                model = random.choice(brand_info["models"])
                article = generate_article(brand_name, model, source_info)
                article["publish_time"] = datetime.now() - timedelta(
                    hours=random.randint(1, 72)
                )
                articles.append(article)

        return articles

    def _save_article(self, source, data: dict) -> Article:
        """保存文章到数据库（去重）"""
        existing = Article.query.filter_by(
            source_id=source.id, url=data["url"]
        ).first()
        if existing:
            return None

        from app.models import Brand, CarModel
        brand = Brand.query.filter_by(name_cn=data.get("brand_name")).first()
        model = None
        if brand and data.get("model_name"):
            model = CarModel.query.filter_by(
                brand_id=brand.id, name_cn=data["model_name"]
            ).first()

        article = Article(
            source_id=source.id,
            brand_id=brand.id if brand else None,
            model_id=model.id if model else None,
            title=data.get("title"),
            content=data.get("content"),
            summary=data.get("summary"),
            url=data["url"],
            author=data.get("author"),
            publish_time=data.get("publish_time"),
            view_count=data.get("view_count", 0),
            like_count=data.get("like_count", 0),
            comment_count=data.get("comment_count", 0),
            share_count=data.get("share_count", 0),
        )
        db.session.add(article)
        db.session.flush()

        # 保存评论
        for c_data in data.get("comments", []):
            comment = Comment(
                article_id=article.id,
                content=c_data.get("content", ""),
                author=c_data.get("author"),
                like_count=c_data.get("like_count", 0),
            )
            db.session.add(comment)
            db.session.flush()

            # 评论情感分析
            c_result = self.analyzer.analyze(c_data.get("content", ""))
            c_sentiment = SentimentResult(
                target_type="comment",
                target_id=comment.id,
                score=c_result["score"],
                label=c_result["label"],
                keywords=c_result["keywords"],
                aspects=c_result["aspects"],
            )
            db.session.add(c_sentiment)

        return article

    def _analyze_and_save(self, article: Article, data: dict):
        """对文章进行情感分析并保存结果"""
        text = f"{article.title}。{article.content}" if article.content else article.title
        result = self.analyzer.analyze(text)

        sentiment = SentimentResult(
            target_type="article",
            target_id=article.id,
            score=result["score"],
            label=result["label"],
            keywords=result["keywords"],
            aspects=result["aspects"],
        )
        db.session.add(sentiment)
