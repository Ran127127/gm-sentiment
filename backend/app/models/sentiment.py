from datetime import datetime
from app.extensions import db


class SentimentResult(db.Model):
    __tablename__ = "sentiment_results"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    target_type = db.Column(db.String(10), nullable=False)  # 'article' or 'comment'
    target_id = db.Column(db.BigInteger, nullable=False)
    score = db.Column(db.Float, nullable=False)  # 0.0~1.0
    label = db.Column(db.String(10), nullable=False)  # positive/negative/neutral
    keywords = db.Column(db.JSON)  # ["空间大", "油耗低"]
    aspects = db.Column(db.JSON)  # {"外观": 0.8, "动力": 0.3}
    model_version = db.Column(db.String(30), default="snownlp_v1")
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("target_type", "target_id", name="uk_target"),
        db.Index("idx_label", "label"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "score": round(self.score, 4),
            "label": self.label,
            "keywords": self.keywords or [],
            "aspects": self.aspects or {},
            "model_version": self.model_version,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }
