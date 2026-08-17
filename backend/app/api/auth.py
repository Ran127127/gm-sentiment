from flask import request
from flask_jwt_extended import create_access_token, jwt_required
from app.api import api_bp
from app.utils.response import success_response, error_response


@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    # MVP: 单管理员硬编码认证，生产环境应查数据库
    if username == "admin" and password == "gm2026":
        token = create_access_token(identity=username)
        return success_response({"access_token": token})
    return error_response("用户名或密码错误", 401)


@api_bp.route("/auth/verify", methods=["GET"])
@jwt_required()
def verify():
    return success_response({"authenticated": True})
