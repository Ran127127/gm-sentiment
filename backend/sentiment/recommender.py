from datetime import date, timedelta
from app.extensions import db
from app.models import Brand, CarModel, DailySummary, Recommendation, SentimentResult, Article
from sqlalchemy import func


class RecommendationEngine:
    """基于规则的舆情建议生成引擎"""

    def generate_for_brand(self, brand_id: int, target_date: date = None) -> list:
        """为指定品牌生成建议"""
        if target_date is None:
            target_date = date.today()

        brand = Brand.query.get(brand_id)
        if not brand:
            return []

        # 获取近7天汇总数据
        week_ago = target_date - timedelta(days=7)
        summaries = DailySummary.query.filter(
            DailySummary.brand_id == brand_id,
            DailySummary.date >= week_ago,
            DailySummary.date <= target_date,
            DailySummary.model_id.is_(None),
            DailySummary.source_id.is_(None),
        ).all()

        if not summaries:
            return []

        total = sum(s.total_count for s in summaries)
        positive = sum(s.positive_count for s in summaries)
        negative = sum(s.negative_count for s in summaries)
        avg_score = (sum(s.avg_score * s.total_count for s in summaries if s.avg_score)
                     / total) if total > 0 else 0.5

        stats = {
            "brand_name": brand.name_cn,
            "total": total,
            "positive_ratio": positive / total if total > 0 else 0,
            "negative_ratio": negative / total if total > 0 else 0,
            "avg_score": avg_score,
        }

        # 获取维度评分
        stats["aspect_scores"] = self._get_aspect_scores(brand_id)

        # 获取热门关键词
        stats["top_keywords"] = self._get_top_keywords(brand_id, week_ago)

        # 计算舆情量变化
        first_half = sum(s.total_count for s in summaries if s.date < week_ago + timedelta(days=4))
        second_half = sum(s.total_count for s in summaries if s.date >= week_ago + timedelta(days=4))
        stats["volume_change"] = (second_half / first_half - 1) if first_half > 0 else 0

        # 运行规则引擎
        recommendations = []
        for rule in self._get_rules():
            if rule["condition"](stats):
                rec = self._build_recommendation(rule, stats, brand_id, target_date)
                recommendations.append(rec)

        return recommendations

    def generate_all(self, target_date: date = None) -> list:
        """为所有品牌生成建议"""
        if target_date is None:
            target_date = date.today()

        all_recs = []
        for brand in Brand.query.all():
            recs = self.generate_for_brand(brand.id, target_date)
            all_recs.extend(recs)

        # 保存到数据库
        for rec_data in all_recs:
            # 去重：同品牌同日期同类别不重复生成
            existing = Recommendation.query.filter_by(
                brand_id=rec_data["brand_id"],
                date=target_date,
                category=rec_data["category"],
            ).first()
            if not existing:
                rec = Recommendation(**rec_data)
                db.session.add(rec)

        db.session.commit()
        return all_recs

    def _get_aspect_scores(self, brand_id: int) -> dict:
        """获取品牌各维度评分"""
        sentiments = SentimentResult.query.filter(
            SentimentResult.target_type == "article",
            SentimentResult.aspects.isnot(None),
            SentimentResult.target_id.in_(
                db.session.query(Article.id).filter_by(brand_id=brand_id)
            ),
        ).all()

        aspect_scores = {}
        for s in sentiments:
            if s.aspects:
                for aspect, score in s.aspects.items():
                    if aspect not in aspect_scores:
                        aspect_scores[aspect] = []
                    aspect_scores[aspect].append(score)

        return {
            k: sum(v) / len(v)
            for k, v in aspect_scores.items()
        }

    def _get_top_keywords(self, brand_id: int, since: date) -> list:
        """获取热门关键词"""
        kw_freq = {}
        sentiments = SentimentResult.query.filter(
            SentimentResult.target_type == "article",
            SentimentResult.keywords.isnot(None),
            SentimentResult.target_id.in_(
                db.session.query(Article.id).filter(
                    Article.brand_id == brand_id,
                    Article.publish_time >= since.isoformat(),
                )
            ),
        ).all()

        for s in sentiments:
            if s.keywords:
                for kw in s.keywords:
                    kw_freq[kw] = kw_freq.get(kw, 0) + 1

        return [k for k, _ in sorted(kw_freq.items(), key=lambda x: -x[1])[:10]]

    def _get_rules(self) -> list:
        """定义规则集"""
        return [
            {
                "condition": lambda s: s["negative_ratio"] > 0.35,
                "category": "pr_crisis",
                "priority": "high",
                "template": (
                    "【舆情预警】{brand_name}近7天负面舆情占比达{negative_ratio:.0%}，"
                    "建议启动公关预案。主要负面话题: {top_keywords}"
                ),
            },
            {
                "condition": lambda s: s.get("aspect_scores", {}).get("性价比", 1) < 0.4,
                "category": "marketing",
                "priority": "medium",
                "template": (
                    "【营销建议】{brand_name}用户普遍反映性价比感知不足，"
                    "建议加强金融方案宣传或增加配置亮点传播。"
                ),
            },
            {
                "condition": lambda s: abs(s.get("volume_change", 0)) > 0.5,
                "category": "opportunity",
                "priority": "medium",
                "template": (
                    "【传播机会】{brand_name}讨论量较上周变化{volume_change:+.0%}，"
                    "建议趁热度调整内容投放策略。"
                ),
            },
            {
                "condition": lambda s: any(
                    s.get("aspect_scores", {}).get(a, 1) < 0.35
                    for a in ["动力", "空间", "内饰"]
                ),
                "category": "product_feedback",
                "priority": "medium",
                "template": (
                    "【产品反馈】{brand_name}用户集中反馈以下维度不满意: "
                    "{weak_aspects}。建议反馈至产品部门作为改款参考。"
                ),
            },
            {
                "condition": lambda s: s["avg_score"] > 0.7 and s["total"] > 100,
                "category": "marketing",
                "priority": "low",
                "template": (
                    "【正面传播】{brand_name}近期口碑表现优秀（正面率{positive_ratio:.0%}），"
                    "建议加大正面内容投放，巩固品牌好感度。"
                ),
            },
        ]

    def _build_recommendation(self, rule: dict, stats: dict,
                              brand_id: int, target_date: date) -> dict:
        """构建建议对象"""
        template = rule["template"]

        # 填充弱项维度
        weak_aspects = []
        for aspect in ["动力", "空间", "内饰"]:
            if stats.get("aspect_scores", {}).get(aspect, 1) < 0.35:
                weak_aspects.append(aspect)

        try:
            title = template.format(
                weak_aspects="、".join(weak_aspects) if weak_aspects else "部分维度",
                **stats,
            )
        except (KeyError, IndexError):
            title = template

        return {
            "date": target_date,
            "brand_id": brand_id,
            "model_id": None,
            "category": rule["category"],
            "priority": rule["priority"],
            "title": title[:200],
            "description": title,
            "evidence": {
                "avg_score": stats["avg_score"],
                "negative_ratio": stats["negative_ratio"],
                "total": stats["total"],
                "top_keywords": stats.get("top_keywords", [])[:5],
            },
            "status": "pending",
        }
