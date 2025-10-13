from flask import Blueprint, request, jsonify
from services.database import Supa


db = Supa()

feedback_bp = Blueprint("feedback", __name__, url_prefix="/feedback")

@feedback_bp.route("/<location_id>/<operator_id>", methods=["POST"])
def submit_feedback(location_id, operator_id):
    """
    Submit/update monthly feedback for an operator
    DEPRECATED: This endpoint appears to be incomplete and may not be in use.
    Consider using the AI-generated feedback system instead.
    """
    try:
        data = request.get_json()

        if not data or "feedback" not in data:
            return jsonify({
                "success": False,
                "error": "Feedback data is required"
            }), 400

        # Store the feedback
        db.insert_operator_feedback(operator_id, data["feedback"])

        return jsonify({
            "success": True,
            "message": "Feedback submitted successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@feedback_bp.route("/<operator_id>", methods=["GET"])
def get_feedback(operator_id):
    """
    Get monthly feedback for an operator
    """
    try:
        feedback = db.get_operator_monthly_feedback(operator_id)

        return jsonify({
            "success": True,
            "data": {
                "operator_id": operator_id,
                "monthly_feedback": feedback
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500