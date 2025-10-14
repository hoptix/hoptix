from flask import current_app, request, Blueprint, jsonify, g
import logging
from services.database import Supa
from utils.helpers import convert_item_ids_to_names
from services.items import ItemLookupService
from services.auth_helpers import verify_run_ownership, verify_location_ownership, get_user_locations
from services.ai_feedback import get_ai_feedback
from middleware.auth import require_auth

db = Supa()

runs_bp = Blueprint("runs", __name__)


logger = logging.getLogger(__name__)

@runs_bp.get("/runs")
@require_auth
def get_all_runs():
    try:
        # Get user's locations
        user_location_ids = get_user_locations(g.user_id)

        if not user_location_ids:
            return jsonify({"runs": []}), 200

        # Get runs for user's locations only
        res = db.client.table("runs").select("*").in_("location_id", user_location_ids).execute()
        runs = res.data

        if not runs:
            return jsonify({"runs": []}), 200

        # OPTIMIZATION: Batch fetch all analytics data at once to avoid N+1 queries
        run_ids = [run["id"] for run in runs]
        analytics_result = db.client.table("run_analytics").select("*").in_("run_id", run_ids).execute()

        # Create a lookup dictionary for O(1) access: {run_id: analytics_data}
        analytics_dict = {}
        if analytics_result.data:
            for analytics in analytics_result.data:
                analytics_dict[analytics["run_id"]] = analytics

        # Process each run to add analytics data using the lookup dictionary
        for run in runs:
            try:
                analytics = analytics_dict.get(run["id"])

                if analytics:
                    # Add analytics fields to the run object
                    run["total_transcriptions"] = analytics.get("total_transactions", 0)
                    run["successful_upsells"] = analytics.get("upsell_successes", 0)
                    run["successful_upsizes"] = analytics.get("upsize_successes", 0)
                    run["total_revenue"] = float(analytics.get("upsell_revenue", 0) or 0) + float(analytics.get("addon_revenue", 0) or 0) + float(analytics.get("upsize_revenue", 0) or 0)
                else:
                    # No analytics data found, set defaults
                    run["total_transcriptions"] = 0
                    run["successful_upsells"] = 0
                    run["successful_upsizes"] = 0
                    run["total_revenue"] = 0.0

            except Exception as e:
                logger.error(f"Error processing analytics for run {run.get('id', 'unknown')}: {str(e)}")
                # Set defaults if analytics processing fails
                run["total_transcriptions"] = 0
                run["successful_upsells"] = 0
                run["successful_upsizes"] = 0
                run["total_revenue"] = 0.0

        # Filter out runs with 0 transactions
        filtered_runs = [run for run in runs if run.get("total_transcriptions", 0) > 0]

        return jsonify({"runs": filtered_runs}), 200

    except Exception as e:
        logger.error(f"Error fetching runs: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@runs_bp.get("/locations")
@require_auth
def get_all_locations():
    """Get all locations owned by the authenticated user (or all locations if admin)"""

    try:
        logger.info(f"Fetching locations for user {g.user_id} (is_admin={g.is_admin})...")

        # Admin users get all locations, regular users get only their own
        if g.is_admin:
            logger.info(f"Admin user {g.user_id} - fetching all locations")
            locations_result = db.client.table("locations").select("*").execute()
        else:
            logger.info(f"Regular user {g.user_id} - fetching owned locations only")
            locations_result = db.client.table("locations").select("*").eq("owner_id", g.user_id).execute()

        if not locations_result.data:
            logger.info("No locations found for this user")
            return {"locations": [], "count": 0}, 200

        logger.info(f"Found {len(locations_result.data)} locations for user {g.user_id}")
        
        # Get all organizations to map org_id to org_name
        orgs_result = db.client.table("orgs").select("id, name").execute()
        orgs_map = {org["id"]: org["name"] for org in orgs_result.data} if orgs_result.data else {}
        
        logger.info(f"Found {len(orgs_map)} organizations")
        
        # Transform the data to include organization name
        locations = []
        for location in locations_result.data:
            org_name = orgs_map.get(location.get("org_id"), "Unknown Organization")
            locations.append({
                "id": location.get("id"),
                "name": location.get("name"),
                "org_id": location.get("org_id"),
                "org_name": org_name,
                "timezone": location.get("tz", ""),
                "created_at": location.get("created_at", ""),
                "display_name": f"{org_name} - {location.get('name', 'Unknown Location')}"
            })
        
        logger.info(f"Successfully retrieved {len(locations)} locations")
        return {"locations": locations, "count": len(locations)}, 200
        
    except Exception as e:
        logger.error(f"Error retrieving locations: {str(e)}", exc_info=True)
        return {"error": f"Internal server error: {str(e)}"}, 500

@runs_bp.get("/locations/<location_id>/runs")
@require_auth
def get_runs_by_location(location_id):
    """Get all runs for a specific location with analytics data"""

    try:
        # Verify user owns this location
        if not verify_location_ownership(g.user_id, location_id):
            return jsonify({
                "error": "Access denied: You do not have permission to access this location"
            }), 403
        # Get query parameters
        limit = int(request.args.get("limit", 50))
        limit = min(limit, 200)  # Cap at 200 for performance
        include_analytics = request.args.get("include_analytics", "true").lower() == "true"
        
        if include_analytics:
            # Use the comprehensive view that includes analytics data
            result = db.client.table("run_analytics_with_details").select(
                "run_id, run_date, location_id, org_id, "
                "total_transactions, upsell_successes, upsize_successes, "
                "total_revenue, upsell_revenue, upsize_revenue, addon_revenue"
            ).eq("location_id", location_id).order("run_date", desc=True).limit(limit).execute()
            
            if not result.data:
                return {"runs": [], "count": 0}, 200
            
            # Transform the data from the analytics view
            runs = []
            for row in result.data:
                runs.append({
                    "id": row["run_id"],
                    "runId": row["run_id"],
                    "date": row["run_date"],
                    "status": "ready",  # Analytics view only contains completed runs
                    "created_at": row["run_date"],  # Use run_date as created_at
                    "org_id": row["org_id"],
                    "location_id": row["location_id"],
                    "totalTransactions": row.get("total_transactions", 0),
                    "successfulUpsells": row.get("upsell_successes", 0),
                    "successfulUpsizes": row.get("upsize_successes", 0),
                    "totalRevenue": float(row.get("total_revenue", 0) or 0)
                })
        else:
            # Query basic runs data without analytics
            result = db.client.table("runs").select(
                "id, org_id, location_id, run_date, status, created_at"
            ).eq("location_id", location_id).order("created_at", desc=True).limit(limit).execute()
            
            if not result.data:
                return {"runs": [], "count": 0}, 200
            
            # Transform basic runs data
            runs = []
            for run in result.data:
                runs.append({
                    "id": run["id"],
                    "runId": run["id"],
                    "date": run["run_date"],
                    "status": run["status"],
                    "created_at": run["created_at"],
                    "org_id": run["org_id"],
                    "location_id": run["location_id"]
                })
        
        logger.info(f"Retrieved {len(runs)} runs for location {location_id}")
        return {"runs": runs, "count": len(runs)}, 200
        
    except Exception as e:
        logger.error(f"Error retrieving runs for location {location_id}: {str(e)}", exc_info=True)
        return {"error": f"Internal server error: {str(e)}"}, 500


@runs_bp.route('/runs/<run_id>/transactions', methods=['GET'])
@require_auth
def get_run_transactions(run_id: str):
    """
    Get raw transaction data for a specific run

    Query Parameters:
        limit (int): Number of transactions to return (default: 50, max: 200)
        offset (int): Number of transactions to skip for pagination (default: 0)

    Returns:
        JSON: Transaction data with pagination metadata
    """
    try:
        # Verify user owns this run
        if not verify_run_ownership(g.user_id, run_id):
            return jsonify({
                "success": False,
                "error": "Access denied: You do not have permission to access this run"
            }), 403
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 200)  # Cap at 200
        offset = max(int(request.args.get('offset', 0)), 0)   # Ensure non-negative
        
        # Get transactions directly from graded_rows_filtered view
        # Get count first
        count_result = db.client.table('graded_rows_filtered').select('transaction_id', count='exact').eq('run_id', run_id).execute()
        total_count = count_result.count if count_result.count is not None else 0

        
        # Get the actual data
        result = db.client.table('graded_rows_filtered').select('*').eq('run_id', run_id).order('begin_time', desc=True).range(offset, offset + limit - 1).execute()
        
        # Get location_id from first transaction to initialize item lookup
        location_id = None
        if result.data:
            # print("result.data", result.data)
            # Try to get location_id from run
            run_result = db.client.table('runs').select('location_id').eq('id', run_id).execute()
            location_id = run_result.data[0].get('location_id') if run_result.data else None
        
        # Initialize item lookup service
        item_lookup = ItemLookupService(db, location_id) if location_id else ItemLookupService()
        
        # Process transactions to convert item IDs to names
        processed_transactions = []
        for transaction in result.data if result.data else []:
            # Convert item ID fields to human-readable names
            processed_transaction = transaction.copy()
            
            # List of fields that contain item IDs to convert
            item_fields = [
                'items_initial', 'items_after', 'upsell_candidate_items', 'upsell_offered_items',
                'upsell_success_items', 'upsize_candidate_items', 'upsize_offered_items',
                'upsize_success_items', 'addon_candidate_items', 'addon_offered_items',
                'addon_success_items'
            ]
            
            for field in item_fields:
                if field in processed_transaction:
                    # Save raw version first
                    raw_value = processed_transaction[field]
                    processed_transaction[f"{field}_raw"] = raw_value
                    # Then convert to names
                    converted_value = convert_item_ids_to_names(raw_value, item_lookup)
                    processed_transaction[field] = converted_value
                    logger.info(f"Converted {field}: {raw_value} -> {converted_value}")
                else:
                    logger.debug(f"Field {field} not found in transaction")
            
            processed_transactions.append(processed_transaction)
        
        # Format the result to match expected structure
        result = {
            'transactions': processed_transactions,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': total_count > (offset + limit)
        }

        print("result", result['transactions'][0])
 
        if result['transactions'] or offset == 0:  # Return empty result for valid run, but not if offset is invalid
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'No transactions found for this run'
            }), 404
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid limit or offset parameter'
        }), 400
    except Exception as e:
        logger.error(f"Error retrieving transactions for run {run_id}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500


@runs_bp.route('/runs/<run_id>/ai-feedback', methods=['GET'])
@require_auth
def get_run_ai_feedback(run_id: str):
    """
    Get AI-generated feedback summary for a specific run

    This endpoint aggregates all transaction-level feedback for the run
    and uses AI to generate a consolidated summary with:
    - Top recurring issues with evidence
    - Top recurring strengths with evidence
    - Recommended actions
    - Overall rating

    Returns:
        JSON: AI feedback summary or None if no feedback available
    """
    try:
        # Verify user owns this run
        if not verify_run_ownership(g.user_id, run_id):
            return jsonify({
                "success": False,
                "error": "Access denied: You do not have permission to access this run"
            }), 403

        logger.info(f"Generating AI feedback for run {run_id}")

        # Generate AI feedback for the run
        feedback_json = get_ai_feedback(run_id=run_id)

        if feedback_json is None:
            return jsonify({
                "success": True,
                "data": None,
                "message": "No feedback data available for this run"
            }), 200

        # Parse the JSON string back to dict for response
        import json
        feedback_dict = json.loads(feedback_json)

        return jsonify({
            "success": True,
            "data": {
                "run_id": run_id,
                "feedback": feedback_dict
            }
        }), 200

    except Exception as e:
        logger.error(f"Error generating AI feedback for run {run_id}: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@runs_bp.route('/runs/range-ai-feedback', methods=['GET'])
@require_auth
def get_range_ai_feedback():
    """
    Get AI-generated feedback for multiple runs in a date range

    Query Parameters:
        location_ids[] (list): Location IDs to filter by
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format

    Returns:
        JSON: List of AI feedback summaries for each run in the range
    """
    try:
        from datetime import datetime
        import json
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Get query parameters
        location_ids = request.args.getlist('location_ids[]')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Validate required parameters
        if not location_ids or not start_date_str or not end_date_str:
            return jsonify({
                "success": False,
                "error": "location_ids[], start_date, and end_date are required"
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
        runs_query = db.client.table("runs").select("id, run_date, location_id").in_(
            "location_id", location_ids
        ).gte("run_date", start_date.isoformat()).lte("run_date", end_date.isoformat()).order("run_date", desc=False)

        runs_result = runs_query.execute()

        if not runs_result.data:
            return jsonify({
                "success": True,
                "data": []
            }), 200

        # Extract run IDs
        runs = runs_result.data
        logger.info(f"Generating AI feedback for {len(runs)} runs in date range {start_date} to {end_date}")

        # Function to generate feedback for a single run
        def generate_feedback_for_run(run):
            run_id = run['id']
            try:
                feedback_json = get_ai_feedback(run_id=run_id)

                if feedback_json is None:
                    return {
                        "run_id": run_id,
                        "run_date": run['run_date'],
                        "location_id": run['location_id'],
                        "feedback": None,
                        "has_feedback": False
                    }

                feedback_dict = json.loads(feedback_json)
                return {
                    "run_id": run_id,
                    "run_date": run['run_date'],
                    "location_id": run['location_id'],
                    "feedback": feedback_dict,
                    "has_feedback": True
                }
            except Exception as e:
                logger.error(f"Error generating feedback for run {run_id}: {str(e)}")
                return {
                    "run_id": run_id,
                    "run_date": run['run_date'],
                    "location_id": run['location_id'],
                    "feedback": None,
                    "has_feedback": False,
                    "error": str(e)
                }

        # Generate feedback in parallel for better performance
        # Limit to 5 concurrent requests to avoid overwhelming the OpenAI API
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_run = {executor.submit(generate_feedback_for_run, run): run for run in runs}

            for future in as_completed(future_to_run):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    run = future_to_run[future]
                    logger.error(f"Unexpected error for run {run['id']}: {str(e)}")
                    results.append({
                        "run_id": run['id'],
                        "run_date": run['run_date'],
                        "location_id": run['location_id'],
                        "feedback": None,
                        "has_feedback": False,
                        "error": str(e)
                    })

        # Sort results by run_date
        results.sort(key=lambda x: x['run_date'])

        # Count successful feedbacks
        successful_count = sum(1 for r in results if r['has_feedback'])
        logger.info(f"Successfully generated feedback for {successful_count}/{len(results)} runs")

        return jsonify({
            "success": True,
            "data": results,
            "meta": {
                "total_runs": len(results),
                "runs_with_feedback": successful_count,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }), 200

    except Exception as e:
        logger.error(f"Error in get_range_ai_feedback: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500