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
        
        # Format the response (updated to new schema without per-category revenues)
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
            "upsize_opportunities": result.data["upsize_opportunities"],
            "upsize_offers": result.data["upsize_offers"],
            "upsize_successes": result.data["upsize_successes"],
            "upsize_conversion_rate": float(result.data["upsize_conversion_rate"]),
            "addon_opportunities": result.data["addon_opportunities"],
            "addon_offers": result.data["addon_offers"],
            "addon_successes": result.data["addon_successes"],
            "addon_conversion_rate": float(result.data["addon_conversion_rate"]),
            "total_opportunities": result.data["total_opportunities"],
            "total_offers": result.data["total_offers"],
            "total_successes": result.data["total_successes"],
            "overall_conversion_rate": float(result.data["overall_conversion_rate"]),
            "total_revenue": float(result.data["total_revenue"]),
            "detailed_revenue": result.data.get("detailed_revenue"),  # JSON string/map per schema
            "detailed_analytics": result.data.get("detailed_analytics")  # Keep as JSON string
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

        # Check for worker_id query parameter for filtering
        worker_id = request.args.get('worker_id')

        # Get worker analytics for this run
        if worker_id:
            # Get specific worker analytics
            result = db.client.table("run_analytics_worker").select("*").eq("run_id", run_id).eq("worker_id", worker_id).execute()
        else:
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

        # Fetch all runs at once to avoid N+1 queries
        run_ids = [worker_data['run_id'] for worker_data in result.data]
        runs_result = db.client.table("runs").select("id, run_date, location_id, org_id").in_("id", run_ids).execute()

        # Create lookup dictionaries
        runs_dict = {run['id']: run for run in runs_result.data}

        # Get unique location_ids and org_ids
        unique_location_ids = list(set(run['location_id'] for run in runs_result.data))
        unique_org_ids = list(set(run['org_id'] for run in runs_result.data if run.get('org_id')))

        # Fetch all locations and orgs at once
        locations_result = db.client.table("locations").select("id, name").in_("id", unique_location_ids).execute()
        locations_dict = {loc['id']: loc['name'] for loc in locations_result.data}

        orgs_result = db.client.table("orgs").select("id, name").in_("id", unique_org_ids).execute()
        orgs_dict = {org['id']: org['name'] for org in orgs_result.data}

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

            # Get run data from cache
            run = runs_dict.get(worker_data['run_id'], {})
            location_id = run.get('location_id', 'unknown')
            location_name = locations_dict.get(location_id, 'Unknown Location')
            org_id = run.get('org_id')
            org_name = orgs_dict.get(org_id, 'Unknown Org') if org_id else 'Unknown Org'

            worker_analytics.append({
                "id": f"{worker_data['run_id']}_{worker_data['worker_id']}",  # Unique ID for table
                "run_id": worker_data['run_id'],
                "worker_id": worker_data['worker_id'],
                "run_date": run.get("run_date", "Unknown"),
                "location_id": location_id,
                "location_name": location_name,
                "org_name": org_name,
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


@analytics_bp.route("/analytics/dashboard", methods=["GET"])
@require_auth
def get_multi_location_dashboard_analytics():
    """
    Get aggregated dashboard analytics across multiple locations
    Supports date range filtering and trend comparison
    """
    try:
        from datetime import datetime, timedelta

        # Get query parameters
        location_ids = request.args.getlist('location_ids[]')
        end_date_str = request.args.get('end_date')
        start_date_str = request.args.get('start_date')
        compare_previous = request.args.get('compare_previous', 'true').lower() == 'true'

        # Validate location_ids
        if not location_ids:
            return jsonify({
                "success": False,
                "error": "At least one location_id is required"
            }), 400

        # Verify user owns all requested locations
        for location_id in location_ids:
            if not verify_location_ownership(g.user_id, location_id):
                return jsonify({
                    "success": False,
                    "error": f"Access denied: You do not have permission to access location {location_id}"
                }), 403

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
        ).in_("location_id", location_ids).gte("run_date", start_date.isoformat()).lte("run_date", end_date.isoformat()).execute()

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
            ).in_("location_id", location_ids).gte("run_date", prev_start_date.isoformat()).lte("run_date", prev_end_date.isoformat()).execute()

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


@analytics_bp.route("/analytics/top-operators", methods=["GET"])
@require_auth
def get_top_operators():
    """
    Get top-ranked operators across selected locations and date range
    Returns operators with metrics, monthly feedback, and breakdown by category
    """
    try:
        from datetime import datetime

        # Get query parameters
        location_ids = request.args.getlist('location_ids[]')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        limit = int(request.args.get('limit', 5))

        # Validate location_ids
        if not location_ids:
            return jsonify({
                "success": False,
                "error": "At least one location_id is required"
            }), 400

        # Verify user owns all requested locations
        for location_id in location_ids:
            if not verify_location_ownership(g.user_id, location_id):
                return jsonify({
                    "success": False,
                    "error": f"Access denied: You do not have permission to access location {location_id}"
                }), 403

        # Get all runs for the selected locations within date range
        runs_query = db.client.table("runs").select("id").in_("location_id", location_ids)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            runs_query = runs_query.gte("run_date", start_date.isoformat())

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            runs_query = runs_query.lte("run_date", end_date.isoformat())

        runs_result = runs_query.execute()

        if not runs_result.data:
            return jsonify({
                "success": True,
                "data": []
            })

        run_ids = [run["id"] for run in runs_result.data]

        # Get worker analytics for these runs
        worker_result = db.client.table("run_analytics_worker").select(
            "worker_id, total_transactions, total_opportunities, total_offers, total_successes, "
            "total_revenue, upsell_opportunities, upsell_offers, upsell_successes, upsell_revenue, "
            "upsize_opportunities, upsize_offers, upsize_successes, upsize_revenue, "
            "addon_opportunities, addon_offers, addon_successes, addon_revenue, "
            "overall_conversion_rate"
        ).in_("run_id", run_ids).execute()

        if not worker_result.data:
            return jsonify({
                "success": True,
                "data": []
            })

        # Aggregate metrics by worker_id
        worker_metrics = {}
        for row in worker_result.data:
            worker_id = row["worker_id"]
            if worker_id not in worker_metrics:
                worker_metrics[worker_id] = {
                    "total_transactions": 0,
                    "total_opportunities": 0,
                    "total_offers": 0,
                    "total_successes": 0,
                    "total_revenue": 0.0,
                    "upsell_opportunities": 0,
                    "upsell_offers": 0,
                    "upsell_successes": 0,
                    "upsell_revenue": 0.0,
                    "upsize_opportunities": 0,
                    "upsize_offers": 0,
                    "upsize_successes": 0,
                    "upsize_revenue": 0.0,
                    "addon_opportunities": 0,
                    "addon_offers": 0,
                    "addon_successes": 0,
                    "addon_revenue": 0.0
                }

            worker_metrics[worker_id]["total_transactions"] += row["total_transactions"] or 0
            worker_metrics[worker_id]["total_opportunities"] += row["total_opportunities"] or 0
            worker_metrics[worker_id]["total_offers"] += row["total_offers"] or 0
            worker_metrics[worker_id]["total_successes"] += row["total_successes"] or 0
            worker_metrics[worker_id]["total_revenue"] += float(row["total_revenue"] or 0)
            worker_metrics[worker_id]["upsell_opportunities"] += row["upsell_opportunities"] or 0
            worker_metrics[worker_id]["upsell_offers"] += row["upsell_offers"] or 0
            worker_metrics[worker_id]["upsell_successes"] += row["upsell_successes"] or 0
            worker_metrics[worker_id]["upsell_revenue"] += float(row["upsell_revenue"] or 0)
            worker_metrics[worker_id]["upsize_opportunities"] += row["upsize_opportunities"] or 0
            worker_metrics[worker_id]["upsize_offers"] += row["upsize_offers"] or 0
            worker_metrics[worker_id]["upsize_successes"] += row["upsize_successes"] or 0
            worker_metrics[worker_id]["upsize_revenue"] += float(row["upsize_revenue"] or 0)
            worker_metrics[worker_id]["addon_opportunities"] += row["addon_opportunities"] or 0
            worker_metrics[worker_id]["addon_offers"] += row["addon_offers"] or 0
            worker_metrics[worker_id]["addon_successes"] += row["addon_successes"] or 0
            worker_metrics[worker_id]["addon_revenue"] += float(row["addon_revenue"] or 0)

        # Calculate conversion rates and prepare ranking
        operators_list = []
        for worker_id, metrics in worker_metrics.items():
            # Calculate overall conversion rate
            overall_conversion_rate = (metrics["total_successes"] / metrics["total_offers"] * 100) if metrics["total_offers"] > 0 else 0

            # Calculate offer rate (what percentage of opportunities were offered)
            offer_rate = (metrics["total_offers"] / metrics["total_opportunities"] * 100) if metrics["total_opportunities"] > 0 else 0

            # Calculate category conversion rates
            upsell_conversion_rate = (metrics["upsell_successes"] / metrics["upsell_offers"] * 100) if metrics["upsell_offers"] > 0 else 0
            upsize_conversion_rate = (metrics["upsize_successes"] / metrics["upsize_offers"] * 100) if metrics["upsize_offers"] > 0 else 0
            addon_conversion_rate = (metrics["addon_successes"] / metrics["addon_offers"] * 100) if metrics["addon_offers"] > 0 else 0

            operators_list.append({
                "worker_id": worker_id,
                "overall_conversion_rate": overall_conversion_rate,
                "total_revenue": metrics["total_revenue"],
                "metrics": {
                    "total_transactions": metrics["total_transactions"],
                    "total_revenue": round(metrics["total_revenue"], 2),
                    "offer_rate": round(offer_rate, 1),
                    "conversion_rate": round(overall_conversion_rate, 1),
                    "total_opportunities": metrics["total_opportunities"],
                    "total_offers": metrics["total_offers"],
                    "total_successes": metrics["total_successes"]
                },
                "breakdown": {
                    "upsell": {
                        "opportunities": metrics["upsell_opportunities"],
                        "offers": metrics["upsell_offers"],
                        "successes": metrics["upsell_successes"],
                        "conversion_rate": round(upsell_conversion_rate, 1),
                        "revenue": round(metrics["upsell_revenue"], 2)
                    },
                    "upsize": {
                        "opportunities": metrics["upsize_opportunities"],
                        "offers": metrics["upsize_offers"],
                        "successes": metrics["upsize_successes"],
                        "conversion_rate": round(upsize_conversion_rate, 1),
                        "revenue": round(metrics["upsize_revenue"], 2)
                    },
                    "addon": {
                        "opportunities": metrics["addon_opportunities"],
                        "offers": metrics["addon_offers"],
                        "successes": metrics["addon_successes"],
                        "conversion_rate": round(addon_conversion_rate, 1),
                        "revenue": round(metrics["addon_revenue"], 2)
                    }
                }
            })

        # Sort by overall conversion rate (descending), then by total revenue as tiebreaker
        operators_list.sort(key=lambda x: (x["overall_conversion_rate"], x["total_revenue"]), reverse=True)

        # Limit to top N operators
        top_operators = operators_list[:limit]

        # Fetch worker display names and monthly feedback from workers table
        worker_ids = [op["worker_id"] for op in top_operators]
        workers_dict = {}

        try:
            workers_result = db.client.table("workers").select("id, display_name, monthly_feedback").in_("id", worker_ids).execute()
            if workers_result.data:
                workers_dict = {worker["id"]: worker for worker in workers_result.data}
        except Exception as e:
            # If workers table query fails, continue without worker info
            print(f"Warning: Could not fetch worker info: {e}")

        # Add rank, name, and monthly feedback
        result = []
        for rank, operator in enumerate(top_operators, start=1):
            worker_id = operator["worker_id"]
            worker_info = workers_dict.get(worker_id, {})

            result.append({
                "rank": rank,
                "worker_id": worker_id,
                "name": worker_info.get("display_name", f"Operator {worker_id[:8]}"),
                "monthly_feedback": worker_info.get("monthly_feedback", ""),
                "metrics": operator["metrics"],
                "breakdown": operator["breakdown"]
            })

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route("/analytics/top-transactions", methods=["GET"])
@require_auth
def get_top_transactions():
    """
    Get recent transactions with AI feedback for selected worker/locations
    Returns transactions with real grader feedback
    """
    try:
        from datetime import datetime

        # Get query parameters
        location_ids = request.args.getlist('location_ids[]')
        worker_id = request.args.get('worker_id')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        limit = int(request.args.get('limit', 10))

        # Validate location_ids
        if not location_ids:
            return jsonify({
                "success": False,
                "error": "At least one location_id is required"
            }), 400

        # Verify user owns all requested locations
        for location_id in location_ids:
            if not verify_location_ownership(g.user_id, location_id):
                return jsonify({
                    "success": False,
                    "error": f"Access denied: You do not have permission to access location {location_id}"
                }), 403

        # Get all runs for the selected locations within date range
        runs_query = db.client.table("runs").select("id, run_date").in_("location_id", location_ids)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            runs_query = runs_query.gte("run_date", start_date.isoformat())

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            runs_query = runs_query.lte("run_date", end_date.isoformat())

        runs_result = runs_query.execute()

        if not runs_result.data:
            return jsonify({
                "success": True,
                "data": []
            })

        run_ids = [run["id"] for run in runs_result.data]
        runs_dict = {run["id"]: run for run in runs_result.data}

        # Query graded transactions from graded_rows_filtered view
        grades_query = db.client.table("graded_rows_filtered").select(
            "transaction_id, run_id, worker_id, transcript, feedback, "
            "num_upsell_opportunities, num_upsell_offers, num_upsell_success, "
            "num_upsize_opportunities, num_upsize_offers, num_upsize_success, "
            "num_addon_opportunities, num_addon_offers, num_addon_success, "
            "begin_time"
        ).in_("run_id", run_ids).order("begin_time", desc=True)

        # Filter by worker_id if provided
        if worker_id:
            grades_query = grades_query.eq("worker_id", worker_id)

        grades_query = grades_query.limit(limit)
        grades_result = grades_query.execute()

        if not grades_result.data:
            return jsonify({
                "success": True,
                "data": []
            })

        # Format response
        transactions = []
        for grade in grades_result.data:
            run = runs_dict.get(grade["run_id"], {})

            transactions.append({
                "id": grade["transaction_id"],
                "run_id": grade["run_id"],
                "run_date": run.get("run_date", ""),
                "worker_id": grade["worker_id"],
                "transaction_text": grade["transcript"],
                "ai_feedback": grade["feedback"],
                "grading": {
                    "upsell": {
                        "opportunities": grade["num_upsell_opportunities"],
                        "offers": grade["num_upsell_offers"],
                        "successes": grade["num_upsell_success"]
                    },
                    "upsize": {
                        "opportunities": grade["num_upsize_opportunities"],
                        "offers": grade["num_upsize_offers"],
                        "successes": grade["num_upsize_success"]
                    },
                    "addon": {
                        "opportunities": grade["num_addon_opportunities"],
                        "offers": grade["num_addon_offers"],
                        "successes": grade["num_addon_success"]
                    }
                },
                "begin_time": grade["begin_time"]
            })

        return jsonify({
            "success": True,
            "data": transactions
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route("/analytics/transactions-by-ids", methods=["GET"])
@require_auth
def get_transactions_by_ids():
    """
    Get transaction details for specific transaction IDs
    Used to fetch transactions mentioned in monthly feedback
    """
    try:
        import logging
        import traceback
        import re
        from datetime import datetime

        # Get query parameters
        transaction_ids = request.args.getlist('transaction_ids[]')
        location_ids = request.args.getlist('location_ids[]')

        logging.info(f"get_transactions_by_ids called with {len(transaction_ids)} transaction IDs and {len(location_ids)} location IDs")

        # Validate UUID format - must be xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        valid_transaction_ids = []
        invalid_transaction_ids = []

        for tid in transaction_ids:
            tid_clean = tid.strip()
            if uuid_pattern.match(tid_clean):
                valid_transaction_ids.append(tid_clean)
            else:
                invalid_transaction_ids.append(tid_clean)

        if invalid_transaction_ids:
            logging.warning(f"Filtered out {len(invalid_transaction_ids)} invalid transaction IDs: {invalid_transaction_ids}")

        # Use only valid transaction IDs for the query
        transaction_ids = valid_transaction_ids

        if not transaction_ids:
            logging.warning("No valid transaction IDs after validation")
            return jsonify({
                "success": True,
                "data": [],
                "warning": f"All {len(invalid_transaction_ids)} transaction IDs were invalid"
            })

        logging.info(f"Proceeding with {len(transaction_ids)} valid transaction IDs")

        # Validate location_ids
        if not location_ids:
            return jsonify({
                "success": False,
                "error": "At least one location_id is required"
            }), 400

        # Limit to 100 transaction IDs per request for performance
        if len(transaction_ids) > 100:
            return jsonify({
                "success": False,
                "error": "Maximum 100 transaction IDs allowed per request"
            }), 400

        # Verify user owns all requested locations
        for location_id in location_ids:
            if not verify_location_ownership(g.user_id, location_id):
                return jsonify({
                    "success": False,
                    "error": f"Access denied: You do not have permission to access location {location_id}"
                }), 403

        # Query transactions from graded_rows_filtered view by transaction_ids only
        # Batch queries to avoid URL length issues with large transaction_id lists
        # Split into chunks of 10 to keep URL length manageable
        batch_size = 10
        all_grades = []
        failed_batches = []

        for i in range(0, len(transaction_ids), batch_size):
            batch_ids = transaction_ids[i:i + batch_size]

            try:
                grades_query = db.client.table("graded_rows_filtered").select(
                    "transaction_id, run_id, worker_id, transcript, feedback, "
                    "num_upsell_opportunities, num_upsell_offers, num_upsell_success, "
                    "num_upsize_opportunities, num_upsize_offers, num_upsize_success, "
                    "num_addon_opportunities, num_addon_offers, num_addon_success, "
                    "begin_time"
                ).in_("transaction_id", batch_ids)

                batch_result = grades_query.execute()
                if batch_result.data:
                    all_grades.extend(batch_result.data)
            except Exception as batch_error:
                logging.error(f"Batch {i//batch_size + 1} failed with error: {str(batch_error)}")
                logging.error(f"Failed batch IDs: {batch_ids}")
                failed_batches.append({
                    "batch_number": i//batch_size + 1,
                    "ids": batch_ids,
                    "error": str(batch_error)
                })
                # Continue with next batch instead of failing completely

        if failed_batches:
            logging.warning(f"Failed to fetch {len(failed_batches)} batches out of {(len(transaction_ids) + batch_size - 1) // batch_size} total batches")

        if not all_grades:
            return jsonify({
                "success": True,
                "data": []
            })

        # Get unique run_ids from the transactions
        unique_run_ids = list(set(grade["run_id"] for grade in all_grades))

        # Verify that all runs belong to the authorized locations
        runs_query = db.client.table("runs").select("id, run_date, location_id").in_("id", unique_run_ids)
        runs_result = runs_query.execute()

        if not runs_result.data:
            return jsonify({
                "success": True,
                "data": []
            })

        # Filter runs to only those in authorized locations
        authorized_run_ids = set()
        runs_dict = {}
        for run in runs_result.data:
            if run["location_id"] in location_ids:
                authorized_run_ids.add(run["id"])
                runs_dict[run["id"]] = run

        # Filter transactions to only include those from authorized runs
        authorized_grades = [grade for grade in all_grades if grade["run_id"] in authorized_run_ids]

        if not authorized_grades:
            return jsonify({
                "success": True,
                "data": []
            })

        # Format response
        transactions = []
        for grade in authorized_grades:
            run = runs_dict.get(grade["run_id"], {})

            transactions.append({
                "id": grade["transaction_id"],
                "run_id": grade["run_id"],
                "run_date": run.get("run_date", ""),
                "worker_id": grade["worker_id"],
                "transaction_text": grade["transcript"],
                "ai_feedback": grade["feedback"],
                "grading": {
                    "upsell": {
                        "opportunities": grade["num_upsell_opportunities"],
                        "offers": grade["num_upsell_offers"],
                        "successes": grade["num_upsell_success"]
                    },
                    "upsize": {
                        "opportunities": grade["num_upsize_opportunities"],
                        "offers": grade["num_upsize_offers"],
                        "successes": grade["num_upsize_success"]
                    },
                    "addon": {
                        "opportunities": grade["num_addon_opportunities"],
                        "offers": grade["num_addon_offers"],
                        "successes": grade["num_addon_success"]
                    }
                },
                "begin_time": grade["begin_time"]
            })

        return jsonify({
            "success": True,
            "data": transactions
        })

    except Exception as e:
        logging.error(f"Error in get_transactions_by_ids: {str(e)}")
        logging.error(f"Full traceback:\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route("/analytics/range-report", methods=["GET"])
@require_auth
def get_range_report():
    """
    Generate consolidated analytics report for a custom date range across multiple locations
    Aggregates data from all runs within the range and returns in same format as single-run reports
    """
    try:
        import json
        from datetime import datetime
        from collections import defaultdict

        # Get query parameters
        location_ids = request.args.getlist('location_ids[]')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Validate required parameters
        if not location_ids:
            return jsonify({
                "success": False,
                "error": "At least one location_id is required"
            }), 400

        if not start_date_str or not end_date_str:
            return jsonify({
                "success": False,
                "error": "Both start_date and end_date are required"
            }), 400

        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid date format. Use YYYY-MM-DD"
            }), 400

        # Verify user owns all requested locations
        for location_id in location_ids:
            if not verify_location_ownership(g.user_id, location_id):
                return jsonify({
                    "success": False,
                    "error": f"Access denied: You do not have permission to access location {location_id}"
                }), 403

        # Get all runs in the date range for these locations
        runs_query = db.client.table("runs").select("id, run_date, location_id, org_id").in_(
            "location_id", location_ids
        ).gte("run_date", start_date.isoformat()).lte("run_date", end_date.isoformat())

        runs_result = runs_query.execute()

        if not runs_result.data:
            return jsonify({
                "success": False,
                "error": "No runs found in the specified date range for these locations"
            }), 404

        run_ids = [run["id"] for run in runs_result.data]

        # Get all run_analytics records for these runs
        analytics_result = db.client.table("run_analytics").select("*").in_("run_id", run_ids).execute()

        if not analytics_result.data:
            return jsonify({
                "success": False,
                "error": "No analytics data found for runs in this range"
            }), 404

        # Get all worker analytics records for these runs
        worker_analytics_result = db.client.table("run_analytics_worker").select("*").in_("run_id", run_ids).execute()

        # Get location and org names for display
        locations_result = db.client.table("locations").select("id, name").in_("id", location_ids).execute()
        locations_dict = {loc['id']: loc['name'] for loc in locations_result.data} if locations_result.data else {}

        unique_org_ids = list(set(run['org_id'] for run in runs_result.data if run.get('org_id')))
        orgs_result = db.client.table("orgs").select("id, name").in_("id", unique_org_ids).execute()
        orgs_dict = {org['id']: org['name'] for org in orgs_result.data} if orgs_result.data else {}

        # Initialize aggregated metrics
        aggregated = {
            "total_transactions": 0,
            "complete_transactions": 0,
            "avg_items_initial_sum": 0.0,
            "avg_items_final_sum": 0.0,
            "avg_item_increase_sum": 0.0,
            "upsell_opportunities": 0,
            "upsell_offers": 0,
            "upsell_successes": 0,
            "upsell_revenue": 0.0,
            "upsize_opportunities": 0,
            "upsize_offers": 0,
            "upsize_successes": 0,
            "upsize_revenue": 0.0,
            "addon_opportunities": 0,
            "addon_offers": 0,
            "addon_successes": 0,
            "addon_revenue": 0.0,
            "total_opportunities": 0,
            "total_offers": 0,
            "total_successes": 0,
            "total_revenue": 0.0
        }

        # Aggregate data from all runs
        num_runs = len(analytics_result.data)
        merged_detailed_analytics = {}

        for run_analytics in analytics_result.data:
            aggregated["total_transactions"] += run_analytics["total_transactions"] or 0
            aggregated["complete_transactions"] += run_analytics["complete_transactions"] or 0
            aggregated["avg_items_initial_sum"] += float(run_analytics["avg_items_initial"] or 0)
            aggregated["avg_items_final_sum"] += float(run_analytics["avg_items_final"] or 0)
            aggregated["avg_item_increase_sum"] += float(run_analytics["avg_item_increase"] or 0)
            aggregated["upsell_opportunities"] += run_analytics["upsell_opportunities"] or 0
            aggregated["upsell_offers"] += run_analytics["upsell_offers"] or 0
            aggregated["upsell_successes"] += run_analytics["upsell_successes"] or 0
            aggregated["upsell_revenue"] += float(run_analytics["upsell_revenue"] or 0)
            aggregated["upsize_opportunities"] += run_analytics["upsize_opportunities"] or 0
            aggregated["upsize_offers"] += run_analytics["upsize_offers"] or 0
            aggregated["upsize_successes"] += run_analytics["upsize_successes"] or 0
            aggregated["upsize_revenue"] += float(run_analytics["upsize_revenue"] or 0)
            aggregated["addon_opportunities"] += run_analytics["addon_opportunities"] or 0
            aggregated["addon_offers"] += run_analytics["addon_offers"] or 0
            aggregated["addon_successes"] += run_analytics["addon_successes"] or 0
            aggregated["addon_revenue"] += float(run_analytics["addon_revenue"] or 0)
            aggregated["total_opportunities"] += run_analytics["total_opportunities"] or 0
            aggregated["total_offers"] += run_analytics["total_offers"] or 0
            aggregated["total_successes"] += run_analytics["total_successes"] or 0
            aggregated["total_revenue"] += float(run_analytics["total_revenue"] or 0)

            # Merge detailed_analytics JSON
            if run_analytics.get("detailed_analytics"):
                try:
                    detailed = json.loads(run_analytics["detailed_analytics"])
                    for item_id, item_data in detailed.items():
                        if item_id not in merged_detailed_analytics:
                            # Initialize new item with empty metrics
                            merged_detailed_analytics[item_id] = {
                                "name": item_data["name"],
                                "sizes": {},
                                "transitions": {
                                    "1_to_2": 0,
                                    "1_to_3": 0,
                                    "2_to_3": 0
                                }
                            }

                        # Merge size metrics
                        for size_id, size_metrics in item_data.get("sizes", {}).items():
                            if size_id not in merged_detailed_analytics[item_id]["sizes"]:
                                merged_detailed_analytics[item_id]["sizes"][size_id] = {
                                    "upsell_base": 0,
                                    "upsell_candidates": 0,
                                    "upsell_offered": 0,
                                    "upsell_success": 0,
                                    "upsell_base_sold": 0,
                                    "upsell_base_offers": 0,
                                    "upsize_base": 0,
                                    "upsize_candidates": 0,
                                    "upsize_offered": 0,
                                    "upsize_success": 0,
                                    "upsize_base_sold": 0,
                                    "upsize_base_offers": 0,
                                    "addon_base": 0,
                                    "addon_candidates": 0,
                                    "addon_offered": 0,
                                    "addon_success": 0,
                                    "addon_base_sold": 0,
                                    "addon_base_offers": 0
                                }

                            # Sum all metrics for this size
                            for metric_key in size_metrics:
                                current_value = merged_detailed_analytics[item_id]["sizes"][size_id].get(metric_key, 0)
                                merged_detailed_analytics[item_id]["sizes"][size_id][metric_key] = current_value + size_metrics[metric_key]

                        # Merge transitions
                        for transition_key in ["1_to_2", "1_to_3", "2_to_3"]:
                            merged_detailed_analytics[item_id]["transitions"][transition_key] += item_data.get("transitions", {}).get(transition_key, 0)

                except json.JSONDecodeError:
                    # Skip invalid JSON
                    pass

        # Calculate averages and conversion rates
        completion_rate = (aggregated["complete_transactions"] / aggregated["total_transactions"] * 100) if aggregated["total_transactions"] > 0 else 0
        avg_items_initial = aggregated["avg_items_initial_sum"] / num_runs if num_runs > 0 else 0
        avg_items_final = aggregated["avg_items_final_sum"] / num_runs if num_runs > 0 else 0
        avg_item_increase = aggregated["avg_item_increase_sum"] / num_runs if num_runs > 0 else 0
        upsell_conversion_rate = (aggregated["upsell_successes"] / aggregated["upsell_offers"] * 100) if aggregated["upsell_offers"] > 0 else 0
        upsize_conversion_rate = (aggregated["upsize_successes"] / aggregated["upsize_offers"] * 100) if aggregated["upsize_offers"] > 0 else 0
        addon_conversion_rate = (aggregated["addon_successes"] / aggregated["addon_offers"] * 100) if aggregated["addon_offers"] > 0 else 0
        overall_conversion_rate = (aggregated["total_successes"] / aggregated["total_offers"] * 100) if aggregated["total_offers"] > 0 else 0

        # Format location names list
        location_names = [locations_dict.get(loc_id, f"Location {loc_id[:8]}") for loc_id in location_ids]

        # Build main analytics response (mimics single run format)
        analytics_data = {
            "run_id": "range",  # Special identifier for range reports
            "run_date": f"{start_date.isoformat()} - {end_date.isoformat()}",
            "location_names": location_names,
            "location_ids": location_ids,
            "num_runs": num_runs,
            "total_transactions": aggregated["total_transactions"],
            "complete_transactions": aggregated["complete_transactions"],
            "completion_rate": round(completion_rate, 2),
            "avg_items_initial": round(avg_items_initial, 2),
            "avg_items_final": round(avg_items_final, 2),
            "avg_item_increase": round(avg_item_increase, 2),
            "upsell_opportunities": aggregated["upsell_opportunities"],
            "upsell_offers": aggregated["upsell_offers"],
            "upsell_successes": aggregated["upsell_successes"],
            "upsell_conversion_rate": round(upsell_conversion_rate, 2),
            "upsell_revenue": round(aggregated["upsell_revenue"], 2),
            "upsize_opportunities": aggregated["upsize_opportunities"],
            "upsize_offers": aggregated["upsize_offers"],
            "upsize_successes": aggregated["upsize_successes"],
            "upsize_conversion_rate": round(upsize_conversion_rate, 2),
            "upsize_revenue": round(aggregated["upsize_revenue"], 2),
            "addon_opportunities": aggregated["addon_opportunities"],
            "addon_offers": aggregated["addon_offers"],
            "addon_successes": aggregated["addon_successes"],
            "addon_conversion_rate": round(addon_conversion_rate, 2),
            "addon_revenue": round(aggregated["addon_revenue"], 2),
            "total_opportunities": aggregated["total_opportunities"],
            "total_offers": aggregated["total_offers"],
            "total_successes": aggregated["total_successes"],
            "overall_conversion_rate": round(overall_conversion_rate, 2),
            "total_revenue": round(aggregated["total_revenue"], 2),
            "detailed_analytics": json.dumps(merged_detailed_analytics)
        }

        # Aggregate worker analytics by worker_id
        worker_aggregated = {}
        if worker_analytics_result.data:
            for worker_data in worker_analytics_result.data:
                worker_id = worker_data["worker_id"]
                if worker_id not in worker_aggregated:
                    worker_aggregated[worker_id] = {
                        "worker_id": worker_id,
                        "total_transactions": 0,
                        "complete_transactions": 0,
                        "avg_items_initial_sum": 0.0,
                        "avg_items_final_sum": 0.0,
                        "avg_item_increase_sum": 0.0,
                        "upsell_opportunities": 0,
                        "upsell_offers": 0,
                        "upsell_successes": 0,
                        "upsell_revenue": 0.0,
                        "upsize_opportunities": 0,
                        "upsize_offers": 0,
                        "upsize_successes": 0,
                        "upsize_revenue": 0.0,
                        "addon_opportunities": 0,
                        "addon_offers": 0,
                        "addon_successes": 0,
                        "addon_revenue": 0.0,
                        "total_opportunities": 0,
                        "total_offers": 0,
                        "total_successes": 0,
                        "total_revenue": 0.0,
                        "run_count": 0,
                        "detailed_analytics": {}
                    }

                # Aggregate worker metrics
                worker_aggregated[worker_id]["total_transactions"] += worker_data["total_transactions"] or 0
                worker_aggregated[worker_id]["complete_transactions"] += worker_data["complete_transactions"] or 0
                worker_aggregated[worker_id]["avg_items_initial_sum"] += float(worker_data["avg_items_initial"] or 0)
                worker_aggregated[worker_id]["avg_items_final_sum"] += float(worker_data["avg_items_final"] or 0)
                worker_aggregated[worker_id]["avg_item_increase_sum"] += float(worker_data["avg_item_increase"] or 0)
                worker_aggregated[worker_id]["upsell_opportunities"] += worker_data["upsell_opportunities"] or 0
                worker_aggregated[worker_id]["upsell_offers"] += worker_data["upsell_offers"] or 0
                worker_aggregated[worker_id]["upsell_successes"] += worker_data["upsell_successes"] or 0
                worker_aggregated[worker_id]["upsell_revenue"] += float(worker_data["upsell_revenue"] or 0)
                worker_aggregated[worker_id]["upsize_opportunities"] += worker_data["upsize_opportunities"] or 0
                worker_aggregated[worker_id]["upsize_offers"] += worker_data["upsize_offers"] or 0
                worker_aggregated[worker_id]["upsize_successes"] += worker_data["upsize_successes"] or 0
                worker_aggregated[worker_id]["upsize_revenue"] += float(worker_data["upsize_revenue"] or 0)
                worker_aggregated[worker_id]["addon_opportunities"] += worker_data["addon_opportunities"] or 0
                worker_aggregated[worker_id]["addon_offers"] += worker_data["addon_offers"] or 0
                worker_aggregated[worker_id]["addon_successes"] += worker_data["addon_successes"] or 0
                worker_aggregated[worker_id]["addon_revenue"] += float(worker_data["addon_revenue"] or 0)
                worker_aggregated[worker_id]["total_opportunities"] += worker_data["total_opportunities"] or 0
                worker_aggregated[worker_id]["total_offers"] += worker_data["total_offers"] or 0
                worker_aggregated[worker_id]["total_successes"] += worker_data["total_successes"] or 0
                worker_aggregated[worker_id]["total_revenue"] += float(worker_data["total_revenue"] or 0)
                worker_aggregated[worker_id]["run_count"] += 1

                # Merge worker detailed analytics
                if worker_data.get("detailed_analytics"):
                    try:
                        detailed = json.loads(worker_data["detailed_analytics"])
                        for item_id, item_data in detailed.items():
                            if item_id not in worker_aggregated[worker_id]["detailed_analytics"]:
                                worker_aggregated[worker_id]["detailed_analytics"][item_id] = {
                                    "name": item_data["name"],
                                    "sizes": {},
                                    "transitions": {"1_to_2": 0, "1_to_3": 0, "2_to_3": 0}
                                }

                            # Merge worker sizes
                            for size_id, size_metrics in item_data.get("sizes", {}).items():
                                if size_id not in worker_aggregated[worker_id]["detailed_analytics"][item_id]["sizes"]:
                                    worker_aggregated[worker_id]["detailed_analytics"][item_id]["sizes"][size_id] = {
                                        "upsell_base": 0, "upsell_candidates": 0, "upsell_offered": 0,
                                        "upsell_success": 0, "upsell_base_sold": 0, "upsell_base_offers": 0,
                                        "upsize_base": 0, "upsize_candidates": 0, "upsize_offered": 0,
                                        "upsize_success": 0, "upsize_base_sold": 0, "upsize_base_offers": 0,
                                        "addon_base": 0, "addon_candidates": 0, "addon_offered": 0,
                                        "addon_success": 0, "addon_base_sold": 0, "addon_base_offers": 0
                                    }
                                for metric_key in size_metrics:
                                    current_value = worker_aggregated[worker_id]["detailed_analytics"][item_id]["sizes"][size_id].get(metric_key, 0)
                                    worker_aggregated[worker_id]["detailed_analytics"][item_id]["sizes"][size_id][metric_key] = current_value + size_metrics[metric_key]

                            # Merge worker transitions
                            for transition_key in ["1_to_2", "1_to_3", "2_to_3"]:
                                worker_aggregated[worker_id]["detailed_analytics"][item_id]["transitions"][transition_key] += item_data.get("transitions", {}).get(transition_key, 0)
                    except json.JSONDecodeError:
                        pass

        # Format worker analytics for response
        worker_analytics_list = []
        for worker_id, worker_data in worker_aggregated.items():
            run_count = worker_data["run_count"]
            completion_rate = (worker_data["complete_transactions"] / worker_data["total_transactions"] * 100) if worker_data["total_transactions"] > 0 else 0
            avg_items_initial = worker_data["avg_items_initial_sum"] / run_count if run_count > 0 else 0
            avg_items_final = worker_data["avg_items_final_sum"] / run_count if run_count > 0 else 0
            avg_item_increase = worker_data["avg_item_increase_sum"] / run_count if run_count > 0 else 0
            upsell_conversion_rate = (worker_data["upsell_successes"] / worker_data["upsell_offers"] * 100) if worker_data["upsell_offers"] > 0 else 0
            upsize_conversion_rate = (worker_data["upsize_successes"] / worker_data["upsize_offers"] * 100) if worker_data["upsize_offers"] > 0 else 0
            addon_conversion_rate = (worker_data["addon_successes"] / worker_data["addon_offers"] * 100) if worker_data["addon_offers"] > 0 else 0
            overall_conversion_rate = (worker_data["total_successes"] / worker_data["total_offers"] * 100) if worker_data["total_offers"] > 0 else 0

            worker_analytics_list.append({
                "worker_id": worker_id,
                "run_id": "range",
                "run_date": f"{start_date.isoformat()} - {end_date.isoformat()}",
                "location_names": location_names,
                "total_transactions": worker_data["total_transactions"],
                "complete_transactions": worker_data["complete_transactions"],
                "completion_rate": round(completion_rate, 2),
                "avg_items_initial": round(avg_items_initial, 2),
                "avg_items_final": round(avg_items_final, 2),
                "avg_item_increase": round(avg_item_increase, 2),
                "upsell_opportunities": worker_data["upsell_opportunities"],
                "upsell_offers": worker_data["upsell_offers"],
                "upsell_successes": worker_data["upsell_successes"],
                "upsell_conversion_rate": round(upsell_conversion_rate, 2),
                "upsell_revenue": round(worker_data["upsell_revenue"], 2),
                "upsize_opportunities": worker_data["upsize_opportunities"],
                "upsize_offers": worker_data["upsize_offers"],
                "upsize_successes": worker_data["upsize_successes"],
                "upsize_conversion_rate": round(upsize_conversion_rate, 2),
                "upsize_revenue": round(worker_data["upsize_revenue"], 2),
                "addon_opportunities": worker_data["addon_opportunities"],
                "addon_offers": worker_data["addon_offers"],
                "addon_successes": worker_data["addon_successes"],
                "addon_conversion_rate": round(addon_conversion_rate, 2),
                "addon_revenue": round(worker_data["addon_revenue"], 2),
                "total_opportunities": worker_data["total_opportunities"],
                "total_offers": worker_data["total_offers"],
                "total_successes": worker_data["total_successes"],
                "overall_conversion_rate": round(overall_conversion_rate, 2),
                "total_revenue": round(worker_data["total_revenue"], 2),
                "detailed_analytics": json.dumps(worker_data["detailed_analytics"])
            })

        return jsonify({
            "success": True,
            "data": {
                "analytics": analytics_data,
                "worker_analytics": worker_analytics_list
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500