from flask import request
from flask_jwt_extended import jwt_required
from app.api import api_bp
from app.extensions import db
from app.models import Recommendation
from app.utils.response import success_response, error_response


@api_bp.route("/recommendations", methods=["GET"])
def list_recommendations():
    """推荐建议列表"""
    brand_id = request.args.get("brand_id", type=int)
    priority = request.args.get("priority")
    status = request.args.get("status")

    query = Recommendation.query
    if brand_id:
        query = query.filter_by(brand_id=brand_id)
    if priority:
        query = query.filter_by(priority=priority)
    if status:
        query = query.filter_by(status=status)

    recs = query.order_by(
        db.case(
            (Recommendation.priority == "high", 1),
            (Recommendation.priority == "medium", 2),
            (Recommendation.priority == "low", 3),
        ),
        Recommendation.date.desc(),
    ).all()

    return success_response([r.to_dict() for r in recs])


@api_bp.route("/recommendations/<int:rec_id>", methods=["GET"])
def get_recommendation(rec_id):
    rec = Recommendation.query.get_or_404(rec_id)
    return success_response(rec.to_dict())


@api_bp.route("/recommendations/<int:rec_id>/acknowledge", methods=["POST"])
@jwt_required()
def acknowledge_recommendation(rec_id):
    rec = Recommendation.query.get_or_404(rec_id)
    rec.status = "acknowledged"
    db.session.commit()
    return success_response(rec.to_dict())
