from flask import Blueprint, current_app, request
from worker.pipeline import process_one_video, claim_video, mark_status
import logging

runs_bp = Blueprint("runs", __name__)

@runs_bp.post("/runs")
def create_run():
    db = current_app.config["DB"]
    body = request.get_json(force=True)

    run_id = db.insert_run(
        org_id=body["org_id"],
        location_id=body["location_id"],
        run_date=body["run_date"]  # "YYYY-MM-DD"
    )
    return {"id": run_id}, 201

@runs_bp.get("/runs/<run_id>")
def read_run(run_id):
    db = current_app.config["DB"]
    data = db.get_run(run_id)
    if not data: return {"error": "not found"}, 404
    return data

@runs_bp.get("/runs")
def list_runs():
    """List runs across all locations, optionally filtered by location, with optional analytics."""
    db = current_app.config["DB"]
    logger = logging.getLogger(__name__)
    
    try:
        # Query parameters
        limit = int(request.args.get("limit", 50))
        limit = min(limit, 200)
        include_analytics = request.args.get("include_analytics", "true").lower() == "true"
        location_id = request.args.get("location_id")
        
        if include_analytics:
            query = db.client.table("run_analytics_with_details").select(
                "run_id, run_date, location_id, org_id, "
                "total_transactions, upsell_successes, upsize_successes, "
                "total_revenue, upsell_revenue, upsize_revenue, addon_revenue"
            )
            if location_id:
                query = query.eq("location_id", location_id)
            result = query.order("run_date", desc=True).limit(limit).execute()
            if not result.data:
                return {"runs": [], "count": 0}, 200
            runs = []
            for row in result.data:
                runs.append({
                    "id": row["run_id"],
                    "runId": row["run_id"],
                    "date": row["run_date"],
                    "status": "ready",
                    "created_at": row["run_date"],
                    "org_id": row["org_id"],
                    "location_id": row["location_id"],
                    "totalTransactions": row.get("total_transactions", 0),
                    "successfulUpsells": row.get("upsell_successes", 0),
                    "successfulUpsizes": row.get("upsize_successes", 0),
                    "totalRevenue": float(row.get("total_revenue", 0) or 0)
                })
        else:
            query = db.client.table("runs").select(
                "id, org_id, location_id, run_date, status, created_at"
            )
            if location_id:
                query = query.eq("location_id", location_id)
            result = query.order("created_at", desc=True).limit(limit).execute()
            if not result.data:
                return {"runs": [], "count": 0}, 200
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
        logger.info(f"Listed {len(runs)} runs" + (f" for location {location_id}" if location_id else ""))
        return {"runs": runs, "count": len(runs)}, 200
    except Exception as e:
        logger.error(f"Error listing runs: {str(e)}", exc_info=True)
        return {"error": f"Internal server error: {str(e)}"}, 500

@runs_bp.get("/locations")
def get_all_locations():
    """Get all locations with their organization details"""
    db = current_app.config["DB"]
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Fetching locations (default: all; filter by owner if provided)...")
        
        owner_id = request.args.get("owner_id")
        
        # Build base query
        query = db.client.table("locations").select("*")
        if owner_id:
            query = query.eq("owner_id", owner_id)
        
        locations_result = query.execute()
        
        if not locations_result.data:
            logger.info("No locations found")
            return {"locations": [], "count": 0}, 200
        
        logger.info(f"Found {len(locations_result.data)} locations" + (f" for owner {owner_id}" if owner_id else ""))
        
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
def get_runs_by_location(location_id):
    """Get all runs for a specific location with analytics data"""
    db = current_app.config["DB"]
    logger = logging.getLogger(__name__)
    
    try:
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



@runs_bp.post("/run-one-video")
def run_one_video():
    """Process one video from SQS queue"""
    logger = logging.getLogger(__name__)
    
    # Get configured services
    sqs = current_app.config["SQS"]
    db = current_app.config["DB"] 
    s3 = current_app.config["S3"]
    
    try:
        # 1. Pop from SQS
        message_data = sqs.receive_video_message(
            wait_time_seconds=1,  # Short wait for API endpoint
            visibility_timeout=1800  # 30 minutes
        )
        
        if not message_data:
            return {"error": "no videos to process"}, 404
        
        # Extract video data from SQS message
        video_data = message_data['video_data']
        receipt_handle = message_data['receipt_handle']
        video_id = video_data['video_id']
        
        logger.info(f"Processing video {video_id} from SQS")
        
        # 2. Claim the video (using the same function as run_once.py)
        if not claim_video(db, video_id):
            # Delete message since video already claimed/processed
            sqs.delete_message(receipt_handle)
            return {"error": f"Could not claim video {video_id} (may already be processing)"}, 409
        
        # 3. Process the video (same as run_once.py)
        video_row = {
            "id": video_data["video_id"],
            "s3_key": video_data["s3_key"], 
            "run_id": video_data["run_id"],
            "location_id": video_data["location_id"],
            "started_at": video_data["started_at"],
            "ended_at": video_data["ended_at"]
        }
        
        process_one_video(db, s3, video_row)
        
        # 4. Mark as processed (using same function as run_once.py)
        mark_status(db, video_id, "ready")
        
        # 5. Delete message from SQS (success)
        sqs.delete_message(receipt_handle)
        
        logger.info(f"✅ Successfully processed video {video_id}")
        return {"message": f"Video {video_id} processed successfully"}, 200
        
    except Exception as e:
        logger.error(f"❌ Failed to process video: {str(e)}")
        
        # Mark as failed and let SQS handle retry
        try:
            if 'video_id' in locals():
                mark_status(db, video_id, "failed")
        except:
            pass  # Don't fail the response if marking fails
            
        # Don't delete message - let it retry via SQS
        return {"error": f"Failed to process video: {str(e)}"}, 500
