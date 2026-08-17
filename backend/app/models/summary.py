from datetime import datetime
from app.extensions import db


class DailySummary(db.Model):
    __tablename__ = "daily_summaries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey("car_models.id"))
    source_id = db.Column(db.Integer, db.ForeignKey("data_sources.id"))
    total_count = db.Column(db.Integer, default=0)
    positive_count = db.Column(db.Integer, default=0)
    negative_count = db.Column(db.Integer, default=0)
    neutral_count = db.Column(db.Integer, default=0)
    avg_score = db.Column(db.Float)
    hot_keywords = db.Column(db.JSON)
    top_articles = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    brand = db.relationship("Brand", backref="daily_summaries")
    model = db.relationship("CarModel", backref="daily_summaries")
    source = db.relationship("DataSource", backref="daily_summaries")

    __table_args__ = (
        db.Index("idx_date_brand", "date", "brand_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "brand_id": self.brand_id,
            "model_id": self.model_id,
            "source_id": self.source_id,
            "total_count": self.total_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "avg_score": round(self.avg_score, 4) if self.avg_score else None,
            "hot_keywords": self.hot_keywords or [],
            "top_articles": self.top_articles or [],
        }
