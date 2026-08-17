from flask import jsonify


def success_response(data=None, message="success", status_code=200):
    resp = {
        "code": 200,
        "message": message,
        "data": data,
    }
    return jsonify(resp), status_code


def paginated_response(items, total, page, size):
    resp = {
        "code": 200,
        "message": "success",
        "data": items,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size if size > 0 else 0,
        },
    }
    return jsonify(resp), 200


def error_response(message="error", status_code=400, data=None):
    resp = {
        "code": status_code,
        "message": message,
        "data": data,
    }
    return jsonify(resp), status_code
