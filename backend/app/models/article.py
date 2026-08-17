from datetime import datetime
from app.extensions import db


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.Integer, db.ForeignKey("data_sources.id"), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"))
    model_id = db.Column(db.Integer, db.ForeignKey("car_models.id"))
    title = db.Column(db.String(500))
    content = db.Column(db.Text)
    summary = db.Column(db.String(1000))
    url = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(100))
    publish_time = db.Column(db.DateTime)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    share_count = db.Column(db.Integer, default=0)
    raw_data = db.Column(db.JSON)

    source = db.relationship("DataSource", backref="articles")
    comments = db.relationship("Comment", backref="article", lazy="dynamic",
                               cascade="all, delete-orphan")
    sentiment = db.relationship("SentimentResult", backref="article",
                                uselist=False, cascade="all, delete-orphan",
                                foreign_keys="SentimentResult.target_id",
                                primaryjoin="and_(SentimentResult.target_type=='article', "
                                            "foreign(SentimentResult.target_id)==Article.id)")

    __table_args__ = (
        db.UniqueConstraint("source_id", "url", name="uk_source_url"),
        db.Index("idx_brand_time", "brand_id", "publish_time"),
        db.Index("idx_model_time", "model_id", "publish_time"),
    )

    def to_dict(self, include_content=False):
        data = {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source.display_name if self.source else None,
            "brand_id": self.brand_id,
            "brand_name": self.brand.name_cn if self.brand else None,
            "model_id": self.model_id,
            "model_name": self.model.name_cn if self.model else None,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "author": self.author,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
        }
        if include_content:
            data["content"] = self.content
        return data


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))
    publish_time = db.Column(db.DateTime)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    like_count = db.Column(db.Integer, default=0)
    raw_data = db.Column(db.JSON)

    sentiment = db.relationship("SentimentResult", backref="comment",
                                uselist=False, cascade="all, delete-orphan",
                                foreign_keys="SentimentResult.target_id",
                                primaryjoin="and_(SentimentResult.target_type=='comment', "
                                            "foreign(SentimentResult.target_id)==Comment.id)")

    def to_dict(self):
        return {
            "id": self.id,
            "article_id": self.article_id,
            "content": self.content,
            "author": self.author,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "like_count": self.like_count,
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
        }
