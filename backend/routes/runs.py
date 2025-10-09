from flask import current_app, request, Blueprint, jsonify, g
import logging
from services.database import Supa
from utils.helpers import convert_item_ids_to_names
from services.items import ItemLookupService
from services.auth_helpers import verify_run_ownership, verify_location_ownership, get_user_locations
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

        # Process each run to add analytics data
        for run in runs: 
            try:
                # Get analytics data for this run
                run_analytics = db.client.table("run_analytics").select("*").eq("run_id", run["id"]).execute()
                
                if run_analytics.data and len(run_analytics.data) > 0:
                    analytics = run_analytics.data[0]
                    
                    # Add analytics fields to the run object (using dictionary assignment, not append)
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
    """Get all locations owned by the authenticated user"""

    try:
        logger.info(f"Fetching locations for user {g.user_id}...")

        # Get only the authenticated user's locations
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