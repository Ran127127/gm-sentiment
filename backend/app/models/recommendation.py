from datetime import datetime
from app.extensions import db


class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey("car_models.id"))
    category = db.Column(db.String(30), nullable=False)
    priority = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    evidence = db.Column(db.JSON)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    brand = db.relationship("Brand", backref="recommendations")
    model = db.relationship("CarModel", backref="recommendations")

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "brand_id": self.brand_id,
            "brand_name": self.brand.name_cn if self.brand else None,
            "model_id": self.model_id,
            "model_name": self.model.name_cn if self.model else None,
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence or [],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
