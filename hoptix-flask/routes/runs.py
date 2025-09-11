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
