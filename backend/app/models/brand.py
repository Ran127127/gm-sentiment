from datetime import datetime
from app.extensions import db


class Brand(db.Model):
    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name_cn = db.Column(db.String(20), nullable=False, unique=True)
    name_en = db.Column(db.String(30), nullable=False, unique=True)
    logo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    models = db.relationship("CarModel", backref="brand", lazy="dynamic")
    articles = db.relationship("Article", backref="brand", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name_cn": self.name_cn,
            "name_en": self.name_en,
            "logo_url": self.logo_url,
        }


class CarModel(db.Model):
    __tablename__ = "car_models"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)
    name_cn = db.Column(db.String(50), nullable=False)
    name_en = db.Column(db.String(50))
    category = db.Column(db.String(20))  # sedan, suv, mpv
    launch_date = db.Column(db.Date)
    is_new = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    articles = db.relationship("Article", backref="model", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "name_cn": self.name_cn,
            "name_en": self.name_en,
            "category": self.category,
            "launch_date": self.launch_date.isoformat() if self.launch_date else None,
            "is_new": self.is_new,
        }
