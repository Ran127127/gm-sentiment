from snownlp import SnowNLP
import jieba
import jieba.analyse


class ChineseSentimentAnalyzer:
    """中文汽车舆情情感分析引擎"""

    ASPECT_KEYWORDS = {
        "外观": ["外观", "颜值", "造型", "设计", "前脸", "车尾", "车灯", "轮毂",
                 "车身", "线条", "大灯", "尾灯", "格栅"],
        "内饰": ["内饰", "中控", "做工", "用料", "质感", "屏幕", "座椅",
                 "仪表盘", "方向盘", "氛围灯", "车机", "触控"],
        "动力": ["动力", "加速", "发动机", "变速箱", "油耗", "提速", "换挡",
                 "涡轮", "马力", "扭矩", "混动", "纯电", "续航"],
        "空间": ["空间", "后排", "后备箱", "头部", "腿部", "储物", "轴距",
                 "乘坐", "座椅空间", "行李箱"],
        "性价比": ["性价比", "价格", "优惠", "配置", "保值", "落地价", "裸车价",
                   "终端优惠", "贷款", "金融方案"],
        "操控": ["操控", "方向盘", "底盘", "悬挂", "刹车", "转向", "减震",
                 "过弯", "路感", "指向"],
        "舒适性": ["舒适", "噪音", "隔音", "减震", "空调", "颠簸", "静谧",
                   "NVH", "滤震", "风噪", "胎噪"],
    }

    def analyze(self, text: str) -> dict:
        """对单条文本进行情感分析，返回总体情感 + 维度情感"""
        if not text or not text.strip():
            return {"score": 0.5, "label": "neutral", "aspects": {}, "keywords": []}

        text = text.strip()

        # 总体情感
        try:
            s = SnowNLP(text)
            overall_score = s.sentiments
        except Exception:
            overall_score = 0.5

        # 分类标签
        if overall_score > 0.6:
            label = "positive"
        elif overall_score < 0.4:
            label = "negative"
        else:
            label = "neutral"

        # 维度情感分析
        aspects = self._analyze_aspects(text)

        # 关键词提取
        keywords = self._extract_keywords(text)

        return {
            "score": round(overall_score, 4),
            "label": label,
            "aspects": {k: round(v, 4) for k, v in aspects.items()},
            "keywords": keywords,
        }

    def _analyze_aspects(self, text: str) -> dict:
        """基于关键词匹配的维度情感分析"""
        aspect_scores = {}

        # 按句子拆分
        sentences = text.replace("！", "。").replace("？", "。").split("。")

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            try:
                sent_score = SnowNLP(sentence).sentiments
            except Exception:
                continue

            for aspect, keywords in self.ASPECT_KEYWORDS.items():
                if any(kw in sentence for kw in keywords):
                    if aspect not in aspect_scores:
                        aspect_scores[aspect] = []
                    aspect_scores[aspect].append(sent_score)

        # 计算各维度平均分
        return {
            k: sum(v) / len(v)
            for k, v in aspect_scores.items()
        }

    def _extract_keywords(self, text: str, topk: int = 10) -> list:
        """使用jieba提取关键词"""
        try:
            tags = jieba.analyse.extract_tags(text, topK=topk, withWeight=False)
            return tags
        except Exception:
            return []

    def batch_analyze(self, texts: list) -> list:
        """批量分析"""
        return [self.analyze(t) for t in texts]
