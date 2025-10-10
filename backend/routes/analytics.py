from flask import Blueprint, jsonify, request, g
from services.analytics import Analytics
from services.database import Supa
from services.auth_helpers import verify_run_ownership, verify_location_ownership, get_user_locations
from middleware.auth import require_auth

db = Supa()

# Create blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api')

@analytics_bp.route("/analytics/run/<run_id>", methods=["GET"])
@analytics_bp.route("/analytics/run/<run_id>/<worker_id>", methods=["GET"])
@require_auth
def get_run_analytics(run_id, worker_id=None):
    """Get analytics for a specific run"""
    try:
        # Verify user owns this run
        if not verify_run_ownership(g.user_id, run_id):
            return jsonify({
                "success": False,
                "error": "Access denied: You do not have permission to access this run"
            }), 403
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
        
        run = db.client.table("runs").select("run_date, location_id, org_id").eq("id", result.data["run_id"]).single().execute()
        location_id = run.data["location_id"]
        location_name = db.get_location_name(location_id)
        org_name = db.get_org_name(location_id)
        
        # Format the response
        analytics_data = {
            "run_id": result.data["run_id"],
            "run_date": run.data["run_date"],  # Placeholder since we're not joining with runs table
            "location_id": location_id,  # Placeholder since we're not joining with runs table
            "location_name": location_name,  # Placeholder
            "org_name": org_name,  # Placeholder
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
@require_auth
def get_run_worker_analytics(run_id):
    """Get worker analytics for a specific run"""
    try:
        # Verify user owns this run
        if not verify_run_ownership(g.user_id, run_id):
            return jsonify({
                "success": False,
                "error": "Access denied: You do not have permission to access this run"
            }), 403
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
            
            run = db.client.table("runs").select("run_date, location_id, org_id").eq("id", worker_data['run_id']).single().execute()
            location_id = run.data["location_id"]
            location_name = db.get_location_name(location_id)
            org_name = db.get_org_name(location_id)
            
            worker_analytics.append({
                "worker_id": worker_data['worker_id'],
                "run_id": worker_data['run_id'],
                "run_date": run.data["run_date"],  # Placeholder since we're not joining with runs table
                "location_id": location_id,  # Placeholder since we're not joining with runs table
                "location_name": location_name,  # Placeholder
                "org_name": org_name,  # Placeholder
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
@require_auth
def get_all_worker_analytics():
    """Get all worker analytics data for the data table - filtered by user's locations"""
    try:
        # Get user's locations
        user_location_ids = get_user_locations(g.user_id)

        if not user_location_ids:
            return jsonify({
                "success": True,
                "data": [],
                "message": "No locations found for this user"
            })

        # Get all runs for user's locations
        runs_result = db.client.table("runs").select("id").in_("location_id", user_location_ids).execute()

        if not runs_result.data:
            return jsonify({
                "success": True,
                "data": [],
                "message": "No runs found for this user's locations"
            })

        user_run_ids = [run["id"] for run in runs_result.data]

        # Get worker analytics for user's runs only
        result = db.client.table("run_analytics_worker").select("*").in_("run_id", user_run_ids).execute()

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

            run = db.client.table("runs").select("run_date, location_id, org_id").eq("id", worker_data['run_id']).single().execute()
            location_id = run.data["location_id"]
            location_name = db.get_location_name(location_id)
            org_name = db.get_org_name(location_id)
            
            
            worker_analytics.append({
                "id": f"{worker_data['run_id']}_{worker_data['worker_id']}",  # Unique ID for table
                "run_id": worker_data['run_id'],
                "worker_id": worker_data['worker_id'],
                "run_date": run.data["run_date"],  # Placeholder - we'll need to get this from runs table separately
                "location_id": location_id,  # Placeholder - we'll need to get this from runs table separately
                "location_name": location_name,  # Placeholder
                "org_name": org_name,  # Placeholder
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

@analytics_bp.route("/analytics/location/<location_id>/over_time", methods=["GET"])
@require_auth
def get_location_analytics_over_time(location_id):
    """
    Get time-series analytics data for a specific location
    Returns daily metrics for charting
    """
    try:
        # Verify user owns this location
        if not verify_location_ownership(g.user_id, location_id):
            return jsonify({
                "success": False,
                "error": "Access denied: You do not have permission to access this location"
            }), 403

        from datetime import datetime, timedelta

        # Get query parameters
        days = int(request.args.get('days', 30))
        end_date_str = request.args.get('end_date')
        start_date_str = request.args.get('start_date')

        # Calculate date range
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date()

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = end_date - timedelta(days=days)

        # Query run_analytics_with_details for time-series data
        result = db.client.table("run_analytics_with_details").select(
            "run_date, upsell_revenue, upsize_revenue, addon_revenue, total_revenue, "
            "total_opportunities, total_offers, total_successes, "
            "upsell_opportunities, upsell_offers, upsell_successes, "
            "upsize_opportunities, upsize_offers, upsize_successes, "
            "addon_opportunities, addon_offers, addon_successes"
        ).eq("location_id", location_id).gte("run_date", start_date.isoformat()).lte(
            "run_date", end_date.isoformat()
        ).order("run_date", desc=False).execute()

        # Aggregate data by date (in case multiple runs per day)
        daily_metrics = {}
        for row in result.data:
            date = row["run_date"]
            if date not in daily_metrics:
                daily_metrics[date] = {
                    "date": date,
                    "upsell_revenue": 0.0,
                    "upsize_revenue": 0.0,
                    "addon_revenue": 0.0,
                    "total_revenue": 0.0,
                    "total_opportunities": 0,
                    "total_offers": 0,
                    "total_successes": 0,
                    "upsell_opportunities": 0,
                    "upsell_offers": 0,
                    "upsell_successes": 0,
                    "upsize_opportunities": 0,
                    "upsize_offers": 0,
                    "upsize_successes": 0,
                    "addon_opportunities": 0,
                    "addon_offers": 0,
                    "addon_successes": 0
                }

            daily_metrics[date]["upsell_revenue"] += float(row["upsell_revenue"] or 0)
            daily_metrics[date]["upsize_revenue"] += float(row["upsize_revenue"] or 0)
            daily_metrics[date]["addon_revenue"] += float(row["addon_revenue"] or 0)
            daily_metrics[date]["total_revenue"] += float(row["total_revenue"] or 0)
            daily_metrics[date]["total_opportunities"] += row["total_opportunities"] or 0
            daily_metrics[date]["total_offers"] += row["total_offers"] or 0
            daily_metrics[date]["total_successes"] += row["total_successes"] or 0
            daily_metrics[date]["upsell_opportunities"] += row["upsell_opportunities"] or 0
            daily_metrics[date]["upsell_offers"] += row["upsell_offers"] or 0
            daily_metrics[date]["upsell_successes"] += row["upsell_successes"] or 0
            daily_metrics[date]["upsize_opportunities"] += row["upsize_opportunities"] or 0
            daily_metrics[date]["upsize_offers"] += row["upsize_offers"] or 0
            daily_metrics[date]["upsize_successes"] += row["upsize_successes"] or 0
            daily_metrics[date]["addon_opportunities"] += row["addon_opportunities"] or 0
            daily_metrics[date]["addon_offers"] += row["addon_offers"] or 0
            daily_metrics[date]["addon_successes"] += row["addon_successes"] or 0

        # Calculate conversion rates for overall and per-category
        for date, metrics in daily_metrics.items():
            # Overall conversion rate
            if metrics["total_offers"] > 0:
                metrics["overall_conversion_rate"] = round(
                    (metrics["total_successes"] / metrics["total_offers"]) * 100, 1
                )
            else:
                metrics["overall_conversion_rate"] = 0.0

            # Upsell conversion rate
            if metrics["upsell_offers"] > 0:
                metrics["upsell_conversion_rate"] = round(
                    (metrics["upsell_successes"] / metrics["upsell_offers"]) * 100, 1
                )
            else:
                metrics["upsell_conversion_rate"] = 0.0

            # Upsize conversion rate
            if metrics["upsize_offers"] > 0:
                metrics["upsize_conversion_rate"] = round(
                    (metrics["upsize_successes"] / metrics["upsize_offers"]) * 100, 1
                )
            else:
                metrics["upsize_conversion_rate"] = 0.0

            # Addon conversion rate
            if metrics["addon_offers"] > 0:
                metrics["addon_conversion_rate"] = round(
                    (metrics["addon_successes"] / metrics["addon_offers"]) * 100, 1
                )
            else:
                metrics["addon_conversion_rate"] = 0.0

        # Convert to array sorted by date
        data_array = sorted(daily_metrics.values(), key=lambda x: x["date"])

        return jsonify({
            "success": True,
            "data": data_array,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route("/analytics/location/<location_id>/dashboard", methods=["GET"])
@require_auth
def get_location_dashboard_analytics(location_id):
    """
    Get aggregated dashboard analytics for a specific location
    Supports date range filtering and trend comparison
    """
    try:
        # Verify user owns this location
        if not verify_location_ownership(g.user_id, location_id):
            return jsonify({
                "success": False,
                "error": "Access denied: You do not have permission to access this location"
            }), 403
        from datetime import datetime, timedelta

        # Get query parameters
        end_date_str = request.args.get('end_date')
        start_date_str = request.args.get('start_date')
        compare_previous = request.args.get('compare_previous', 'true').lower() == 'true'

        # Default to last 30 days if not specified
        if not end_date_str:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if not start_date_str:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        # Calculate period length for comparison
        period_days = (end_date - start_date).days

        # Query current period data from run_analytics_with_details view
        current_result = db.client.table("run_analytics_with_details").select(
            "total_opportunities, total_offers, total_successes, total_revenue, "
            "upsell_revenue, upsize_revenue, addon_revenue"
        ).eq("location_id", location_id).gte("run_date", start_date.isoformat()).lte("run_date", end_date.isoformat()).execute()

        # Aggregate current period metrics
        current_metrics = {
            "total_opportunities": 0,
            "total_offers": 0,
            "total_successes": 0,
            "total_revenue": 0.0
        }

        # Only aggregate if data exists, otherwise return zero metrics
        if current_result.data:
            for row in current_result.data:
                current_metrics["total_opportunities"] += row["total_opportunities"] or 0
                current_metrics["total_offers"] += row["total_offers"] or 0
                current_metrics["total_successes"] += row["total_successes"] or 0
                current_metrics["total_revenue"] += float(row["total_revenue"] or 0)

        # Calculate current period rates
        offer_rate = (current_metrics["total_offers"] / current_metrics["total_opportunities"] * 100) if current_metrics["total_opportunities"] > 0 else 0
        conversion_rate = (current_metrics["total_successes"] / current_metrics["total_offers"] * 100) if current_metrics["total_offers"] > 0 else 0

        # Build response
        response_data = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": period_days
            },
            "metrics": {
                "operator_revenue": round(current_metrics["total_revenue"], 2),
                "offer_rate": round(offer_rate, 1),
                "conversion_rate": round(conversion_rate, 1),
                "items_converted": current_metrics["total_successes"]
            },
            "raw_data": {
                "total_opportunities": current_metrics["total_opportunities"],
                "total_offers": current_metrics["total_offers"],
                "total_successes": current_metrics["total_successes"]
            }
        }

        # Calculate trends if requested
        if compare_previous:
            # Calculate previous period dates
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - timedelta(days=period_days)

            # Query previous period data
            prev_result = db.client.table("run_analytics_with_details").select(
                "total_opportunities, total_offers, total_successes, total_revenue"
            ).eq("location_id", location_id).gte("run_date", prev_start_date.isoformat()).lte("run_date", prev_end_date.isoformat()).execute()

            # Aggregate previous period metrics
            prev_metrics = {
                "total_opportunities": 0,
                "total_offers": 0,
                "total_successes": 0,
                "total_revenue": 0.0
            }

            if prev_result.data:
                for row in prev_result.data:
                    prev_metrics["total_opportunities"] += row["total_opportunities"] or 0
                    prev_metrics["total_offers"] += row["total_offers"] or 0
                    prev_metrics["total_successes"] += row["total_successes"] or 0
                    prev_metrics["total_revenue"] += float(row["total_revenue"] or 0)

            # Calculate previous period rates
            prev_offer_rate = (prev_metrics["total_offers"] / prev_metrics["total_opportunities"] * 100) if prev_metrics["total_opportunities"] > 0 else 0
            prev_conversion_rate = (prev_metrics["total_successes"] / prev_metrics["total_offers"] * 100) if prev_metrics["total_offers"] > 0 else 0

            # Calculate percentage changes
            def calc_change(current, previous):
                if previous == 0:
                    return 0 if current == 0 else 100
                return ((current - previous) / previous) * 100

            response_data["trends"] = {
                "operator_revenue_change": round(calc_change(current_metrics["total_revenue"], prev_metrics["total_revenue"]), 1),
                "offer_rate_change": round(calc_change(offer_rate, prev_offer_rate), 1),
                "conversion_rate_change": round(calc_change(conversion_rate, prev_conversion_rate), 1),
                "items_converted_change": round(calc_change(current_metrics["total_successes"], prev_metrics["total_successes"]), 1)
            }

            response_data["previous_period"] = {
                "start_date": prev_start_date.isoformat(),
                "end_date": prev_end_date.isoformat(),
                "metrics": {
                    "operator_revenue": round(prev_metrics["total_revenue"], 2),
                    "offer_rate": round(prev_offer_rate, 1),
                    "conversion_rate": round(prev_conversion_rate, 1),
                    "items_converted": prev_metrics["total_successes"]
                }
            }

        return jsonify({
            "success": True,
            "data": response_data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500