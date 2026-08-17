from datetime import datetime
from app.extensions import db


class DataSource(db.Model):
    __tablename__ = "data_sources"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    display_name = db.Column(db.String(50), nullable=False)
    source_type = db.Column(db.String(20), nullable=False)  # social_media, auto_media
    base_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    config = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "source_type": self.source_type,
            "base_url": self.base_url,
            "is_active": self.is_active,
        }
