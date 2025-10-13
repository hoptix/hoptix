from flask import Blueprint, request, jsonify
from services.database import Supa


db = Supa()

feedback_bp = Blueprint("feedback", __name__, url_prefix="/feedback")

@feedback_bp.route("/<operator_id>", methods=["POST"])
def submit_feedback(operator_id):
    data = request.get_json()
    
    operator_feedback = db.get_operator_monthly_feedback(operator_id, data["feedback"])
    return jsonify(operator_feedback)

