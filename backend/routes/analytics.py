from flask import Blueprint, jsonify, request
from services.analytics import Analytics
from services.database import Supa

db = Supa()

# Create blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api')

@analytics_bp.route("/analytics/run/<run_id>", methods=["GET"])
@analytics_bp.route("/analytics/run/<run_id>/<worker_id>", methods=["GET"])
def get_run_analytics(run_id, worker_id=None):
    """Get analytics for a specific run"""
    try:
        # Get run analytics from database
        if worker_id:
            result = db.client.table("run_analytics_worker").select("*").eq("run_id", run_id).eq("worker_id", worker_id).single().execute()
        else:
            result = db.client.table("run_analytics").select("*").eq("run_id", run_id).single().execute()
            
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
            "run_date": "2025-10-05",  # Placeholder since we're not joining with runs table
            "location_id": "unknown",  # Placeholder since we're not joining with runs table
            "location_name": "Unknown Location",  # Placeholder
            "org_name": "Unknown Organization",  # Placeholder
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
        
        # Add worker_id if provided
        if worker_id:
            analytics_data["worker_id"] = worker_id
        
        return jsonify({
            "success": True,
            "data": analytics_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@analytics_bp.route("/analytics/run/<run_id>/workers", methods=["GET"])
def get_run_worker_analytics(run_id):
    """Get worker analytics for a specific run"""
    try:
        # Get all worker analytics for this run
        result = db.client.table("run_analytics_worker").select("*").eq("run_id", run_id).execute()
        
        if not result.data:
            return jsonify({
                "success": True,
                "data": [],
                "message": "No worker analytics found for this run"
            })
        
        # Format the response
        worker_analytics = []
        for worker_data in result.data:
            # Parse detailed_analytics JSON
            detailed_analytics = {}
            if worker_data.get('detailed_analytics'):
                import json
                try:
                    detailed_analytics = json.loads(worker_data['detailed_analytics'])
                except json.JSONDecodeError:
                    detailed_analytics = {}
            
            worker_analytics.append({
                "worker_id": worker_data['worker_id'],
                "run_id": worker_data['run_id'],
                "run_date": "2025-10-05",  # Placeholder since we're not joining with runs table
                "location_id": "unknown",  # Placeholder since we're not joining with runs table
                "location_name": "Unknown Location",  # Placeholder
                "org_name": "Unknown Organization",  # Placeholder
                "total_transactions": worker_data['total_transactions'],
                "complete_transactions": worker_data['complete_transactions'],
                "completion_rate": float(worker_data['completion_rate']),
                "avg_items_initial": float(worker_data['avg_items_initial']),
                "avg_items_final": float(worker_data['avg_items_final']),
                "avg_item_increase": float(worker_data['avg_item_increase']),
                "upsell_opportunities": worker_data['upsell_opportunities'],
                "upsell_offers": worker_data['upsell_offers'],
                "upsell_successes": worker_data['upsell_successes'],
                "upsell_conversion_rate": float(worker_data['upsell_conversion_rate']),
                "upsell_revenue": float(worker_data['upsell_revenue']),
                "upsize_opportunities": worker_data['upsize_opportunities'],
                "upsize_offers": worker_data['upsize_offers'],
                "upsize_successes": worker_data['upsize_successes'],
                "upsize_conversion_rate": float(worker_data['upsize_conversion_rate']),
                "upsize_revenue": float(worker_data['upsize_revenue']),
                "addon_opportunities": worker_data['addon_opportunities'],
                "addon_offers": worker_data['addon_offers'],
                "addon_successes": worker_data['addon_successes'],
                "addon_conversion_rate": float(worker_data['addon_conversion_rate']),
                "addon_revenue": float(worker_data['addon_revenue']),
                "total_opportunities": worker_data['total_opportunities'],
                "total_offers": worker_data['total_offers'],
                "total_successes": worker_data['total_successes'],
                "overall_conversion_rate": float(worker_data['overall_conversion_rate']),
                "total_revenue": float(worker_data['total_revenue']),
                "detailed_analytics": json.dumps(detailed_analytics),
                "created_at": worker_data['created_at'],
                "updated_at": worker_data['updated_at']
            })
        
        return jsonify({
            "success": True,
            "data": worker_analytics
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@analytics_bp.route("/analytics/workers", methods=["GET"])
def get_all_worker_analytics():
    """Get all worker analytics data for the data table"""
    try:
        # Get all worker analytics data directly from the table
        result = db.client.table("run_analytics_worker").select("*").execute()
        
        if not result.data:
            return jsonify({
                "success": True,
                "data": [],
                "message": "No worker analytics found"
            })
        
        # Format the response for data table
        worker_analytics = []
        for worker_data in result.data:
            # Parse detailed_analytics JSON
            detailed_analytics = {}
            if worker_data.get('detailed_analytics'):
                import json
                try:
                    detailed_analytics = json.loads(worker_data['detailed_analytics'])
                except json.JSONDecodeError:
                    detailed_analytics = {}

                    
            
            worker_analytics.append({
                "id": f"{worker_data['run_id']}_{worker_data['worker_id']}",  # Unique ID for table
                "run_id": worker_data['run_id'],
                "worker_id": worker_data['worker_id'],
                "run_date": "2025-10-05",  # Placeholder - we'll need to get this from runs table separately
                "location_id": "unknown",  # Placeholder - we'll need to get this from runs table separately
                "location_name": "Unknown Location",  # Placeholder
                "org_name": "Unknown Organization",  # Placeholder
                "total_transactions": worker_data['total_transactions'],
                "complete_transactions": worker_data['complete_transactions'],
                "completion_rate": float(worker_data['completion_rate']),
                "avg_items_initial": float(worker_data['avg_items_initial']),
                "avg_items_final": float(worker_data['avg_items_final']),
                "avg_item_increase": float(worker_data['avg_item_increase']),
                "upsell_opportunities": worker_data['upsell_opportunities'],
                "upsell_offers": worker_data['upsell_offers'],
                "upsell_successes": worker_data['upsell_successes'],
                "upsell_conversion_rate": float(worker_data['upsell_conversion_rate']),
                "upsell_revenue": float(worker_data['upsell_revenue']),
                "upsize_opportunities": worker_data['upsize_opportunities'],
                "upsize_offers": worker_data['upsize_offers'],
                "upsize_successes": worker_data['upsize_successes'],
                "upsize_conversion_rate": float(worker_data['upsize_conversion_rate']),
                "upsize_revenue": float(worker_data['upsize_revenue']),
                "addon_opportunities": worker_data['addon_opportunities'],
                "addon_offers": worker_data['addon_offers'],
                "addon_successes": worker_data['addon_successes'],
                "addon_conversion_rate": float(worker_data['addon_conversion_rate']),
                "addon_revenue": float(worker_data['addon_revenue']),
                "total_opportunities": worker_data['total_opportunities'],
                "total_offers": worker_data['total_offers'],
                "total_successes": worker_data['total_successes'],
                "overall_conversion_rate": float(worker_data['overall_conversion_rate']),
                "total_revenue": float(worker_data['total_revenue']),
                "detailed_analytics": json.dumps(detailed_analytics),
                "created_at": worker_data['created_at'],
                "updated_at": worker_data['updated_at']
            })
        
        return jsonify({
            "success": True,
            "data": worker_analytics
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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