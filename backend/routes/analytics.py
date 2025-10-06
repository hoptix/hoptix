from flask import Blueprint, jsonify, request
from services.analytics import Analytics
from services.database import Supa

db = Supa()

# Create blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api')

@analytics_bp.route("/analytics/run/<run_id>/<worker_id>", methods=["GET"])
def get_run_analytics(run_id, worker_id=None):
    """Get analytics for a specific run"""
    try:
        # Get run analytics from database
        if worker_id:
            result = db.client.table("run_analytics_worker").select("""
                *,
                runs!inner(run_date, location_id, org_id),
                locations!inner(name),
                organizations!inner(name)
            """).eq("run_id", run_id).eq("worker_id", worker_id).single().execute()
        else:
            result = db.client.table("run_analytics").select("""
                *,
                runs!inner(run_date, location_id, org_id),
                locations!inner(name),
                organizations!inner(name)
            """).eq("run_id", run_id).single().execute()
            
        if not result.data:
            return jsonify({
                "success": False,
                "error": "No analytics found for this run"
            }), 404
        
        # Parse the detailed analytics JSON
        detailed_analytics = {}
        if result.data.get("detailed_analytics"):
            import json
            try:
                detailed_analytics = json.loads(result.data["detailed_analytics"])
            except:
                detailed_analytics = {}
        
        # Format the response
        analytics_data = {
            "run_id": result.data["run_id"],
            "run_date": result.data["runs"]["run_date"],
            "location_id": result.data["runs"]["location_id"],
            "location_name": result.data["locations"]["name"],
            "org_name": result.data["organizations"]["name"],
            "total_transactions": result.data["total_transactions"],
            "complete_transactions": result.data["complete_transactions"],
            "completion_rate": float(result.data["completion_rate"]),
            "avg_items_initial": float(result.data["avg_items_initial"]),
            "avg_items_final": float(result.data["avg_items_final"]),
            "avg_item_increase": float(result.data["avg_item_increase"]),
            "upsell_opportunities": result.data["upsell_opportunities"],
            "upsell_offers": result.data["upsell_offers"],
            "upsell_successes": result.data["upsell_successes"],
            "upsell_conversion_rate": float(result.data["upsell_conversion_rate"]),
            "upsell_revenue": float(result.data["upsell_revenue"]),
            "upsize_opportunities": result.data["upsize_opportunities"],
            "upsize_offers": result.data["upsize_offers"],
            "upsize_successes": result.data["upsize_successes"],
            "upsize_conversion_rate": float(result.data["upsize_conversion_rate"]),
            "upsize_revenue": float(result.data["upsize_revenue"]),
            "addon_opportunities": result.data["addon_opportunities"],
            "addon_offers": result.data["addon_offers"],
            "addon_successes": result.data["addon_successes"],
            "addon_conversion_rate": float(result.data["addon_conversion_rate"]),
            "addon_revenue": float(result.data["addon_revenue"]),
            "total_opportunities": result.data["total_opportunities"],
            "total_offers": result.data["total_offers"],
            "total_successes": result.data["total_successes"],
            "overall_conversion_rate": float(result.data["overall_conversion_rate"]),
            "total_revenue": float(result.data["total_revenue"]),
            "detailed_analytics": result.data["detailed_analytics"]  # Keep as JSON string
        }
        
        return jsonify({
            "success": True,
            "data": analytics_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@analytics_bp.route("/analytics/over_time", methods=["GET"])
def get_analytics_over_time(run_id, worker_id=None):
    analytics = Analytics(run_id)
    return jsonify(analytics.generate_analytics_over_time())

@analytics_bp.route("/analytics/item_analytics", methods=["GET"])
def get_item_analytics(run_id, worker_id=None):
    analytics = Analytics()
    return jsonify(analytics.get_item_analytics())

@analytics_bp.route("/analytics/item_analytics_over_time", methods=["GET"])
def get_item_analytics_over_time(run_id, worker_id=None):
    analytics = Analytics()
    return jsonify(analytics.generate_item_analytics_over_time())

@analytics_bp.route("/generate_report/<run_id>/<worker_id>", methods=["GET"])
def generate_report(run_id, worker_id=None):
    analytics = Analytics(run_id, worker_id)
    return jsonify(analytics.generate_report())