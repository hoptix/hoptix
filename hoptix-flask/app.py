import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our processing modules
from config import Settings
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from integrations.sqs_client import get_sqs_client
from worker.pipeline import fetch_one_uploaded_video, claim_video, process_one_video, mark_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize global connections (reused across requests)
try:
    settings = Settings()
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    s3 = get_s3(settings.AWS_REGION)
    
    # Initialize SQS client if configured
    sqs_client = None
    if settings.SQS_QUEUE_URL:
        try:
            sqs_client = get_sqs_client(
                settings.AWS_REGION,
                settings.SQS_QUEUE_URL,
                settings.SQS_DLQ_URL
            )
            logger.info("Successfully initialized SQS client")
        except Exception as sqs_error:
            logger.warning(f"Failed to initialize SQS client: {sqs_error}")
            logger.warning("Falling back to direct processing mode")
    else:
        logger.warning("SQS_QUEUE_URL not configured - using direct processing mode")
    
    logger.info("Successfully initialized database and S3 connections")
except Exception as e:
    logger.error(f"Failed to initialize connections: {e}")
    raise

@app.get("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "ok": True, 
        "timestamp": datetime.now().isoformat(),
        "sqs_enabled": sqs_client is not None,
        "queue_url": settings.SQS_QUEUE_URL if sqs_client else None
    })

@app.post("/process-videos")
def process_videos():
    """Process all uploaded videos in the queue"""
    logger.info("=== Starting video processing via API ===")
    start_time = datetime.now()
    
    succeeded = 0
    failed = 0
    processed_ids = []
    
    try:
        # Process all uploaded videos
        while True:
            row = fetch_one_uploaded_video(db)
            if not row:
                logger.info("No more uploaded videos found in queue.")
                break
            
            vid = row["id"]
            s3_key = row.get("s3_key", "unknown")
            logger.info(f"Found video to process - ID: {vid}, S3 Key: {s3_key}")
            
            # Claim the video
            logger.info(f"Attempting to claim video {vid}...")
            if not claim_video(db, vid):
                logger.warning(f"Could not claim video {vid} (another worker may have taken it). Skipping.")
                continue
            logger.info(f"Successfully claimed video {vid}")
            
            # Process the video
            logger.info(f"Starting video processing for {vid}...")
            process_start = datetime.now()
            try:
                process_one_video(db, s3, row)
                process_end = datetime.now()
                process_duration = (process_end - process_start).total_seconds()
                
                mark_status(db, vid, "ready")
                succeeded += 1
                processed_ids.append(vid)
                logger.info(f"✅ Successfully processed video {vid} in {process_duration:.2f} seconds")
                
            except Exception as e:
                process_end = datetime.now()
                process_duration = (process_end - process_start).total_seconds()
                logger.error(f"❌ Error processing video {vid} after {process_duration:.2f} seconds: {str(e)}")
                
                try:
                    mark_status(db, vid, "failed")
                    logger.info(f"Marked video {vid} as failed in database")
                except Exception as mark_error:
                    logger.error(f"Failed to mark video {vid} as failed: {str(mark_error)}")
                failed += 1
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        result = {
            "success": True,
            "message": "Video processing completed",
            "stats": {
                "succeeded": succeeded,
                "failed": failed,
                "total": succeeded + failed,
                "duration_seconds": total_duration,
                "processed_video_ids": processed_ids
            }
        }
        
        logger.info(f"Batch complete. Succeeded: {succeeded}, Failed: {failed}, Total: {succeeded + failed}")
        logger.info(f"=== Batch session completed in {total_duration:.2f} seconds ===")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Fatal error in process_videos(): {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "stats": {
                "succeeded": succeeded,
                "failed": failed,
                "total": succeeded + failed,
                "processed_video_ids": processed_ids
            }
        }), 500

@app.post("/enqueue-videos")
def enqueue_videos():
    """Enqueue all uploaded videos to SQS for processing"""
    if not sqs_client:
        return jsonify({
            "success": False,
            "error": "SQS not configured - use /process-videos for direct processing"
        }), 503
    
    try:
        logger.info("Enqueuing uploaded videos to SQS")
        
        # Get all uploaded videos
        result = db.client.table("videos").select(
            "id, s3_key, run_id, location_id, started_at, ended_at"
        ).eq("status", "uploaded").execute()
        
        videos = result.data
        if not videos:
            return jsonify({
                "success": True,
                "message": "No videos to enqueue",
                "enqueued_count": 0
            })
        
        # Send videos to SQS in batches
        batch_result = sqs_client.send_batch_messages(videos)
        
        logger.info(f"Enqueued {batch_result['successful']} videos, {batch_result['failed']} failed")
        
        # Get updated queue stats
        queue_stats = sqs_client.get_queue_attributes()
        dlq_stats = sqs_client.get_dlq_attributes()
        
        return jsonify({
            "success": True,
            "message": f"Enqueued {batch_result['successful']} videos for processing",
            "enqueued_count": batch_result['successful'],
            "failed_count": batch_result['failed'],
            "queue_stats": queue_stats,
            "dlq_stats": dlq_stats,
            "errors": batch_result['errors'] if batch_result['failed'] > 0 else None
        })
        
    except Exception as e:
        logger.error(f"Error enqueuing videos to SQS: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.post("/enqueue-single-video")
def enqueue_single_video():
    """Enqueue a specific video to SQS by ID"""
    if not sqs_client:
        return jsonify({
            "success": False,
            "error": "SQS not configured"
        }), 503
    
    try:
        data = request.get_json()
        if not data or 'video_id' not in data:
            return jsonify({
                "success": False,
                "error": "video_id is required in request body"
            }), 400
        
        video_id = data['video_id']
        delay_seconds = data.get('delay_seconds', 0)
        
        # Fetch the specific video
        res = db.client.table("videos").select(
            "id, s3_key, run_id, location_id, started_at, ended_at"
        ).eq("id", video_id).limit(1).execute()
        
        if not res.data:
            return jsonify({
                "success": False,
                "error": f"Video {video_id} not found"
            }), 404
        
        video_data = res.data[0]
        
        # Send to SQS
        message_id = sqs_client.send_video_message(video_data, delay_seconds)
        
        return jsonify({
            "success": True,
            "message": f"Video {video_id} enqueued for processing",
            "message_id": message_id,
            "delay_seconds": delay_seconds
        })
        
    except Exception as e:
        logger.error(f"Error enqueuing single video: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.get("/video-status")
def video_status():
    """Get current video processing queue status"""
    try:
        # Get counts by status from database
        uploaded_res = db.client.table("videos").select("id", count="exact").eq("status", "uploaded").execute()
        processing_res = db.client.table("videos").select("id", count="exact").eq("status", "processing").execute()
        ready_res = db.client.table("videos").select("id", count="exact").eq("status", "ready").execute()
        failed_res = db.client.table("videos").select("id", count="exact").eq("status", "failed").execute()
        
        result = {
            "success": True,
            "database_status": {
                "uploaded": uploaded_res.count,
                "processing": processing_res.count,
                "ready": ready_res.count,
                "failed": failed_res.count
            },
            "timestamp": datetime.now().isoformat(),
            "processing_mode": "sqs" if sqs_client else "direct"
        }
        
        # Add SQS queue stats if available
        if sqs_client:
            try:
                queue_stats = sqs_client.get_queue_attributes()
                dlq_stats = sqs_client.get_dlq_attributes()
                
                result["sqs_status"] = {
                    "queue_stats": queue_stats,
                    "dlq_stats": dlq_stats,
                    "queue_url": settings.SQS_QUEUE_URL,
                    "dlq_url": settings.SQS_DLQ_URL
                }
            except Exception as sqs_error:
                result["sqs_status"] = {"error": str(sqs_error)}
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting video status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.post("/process-single-video")
def process_single_video():
    """Process a specific video by ID"""
    try:
        data = request.get_json()
        if not data or 'video_id' not in data:
            return jsonify({
                "success": False,
                "error": "video_id is required in request body"
            }), 400
        
        video_id = data['video_id']
        logger.info(f"Processing single video: {video_id}")
        
        # Fetch the specific video
        res = db.client.table("videos").select(
            "id, s3_key, run_id, location_id, started_at, ended_at"
        ).eq("id", video_id).limit(1).execute()
        
        if not res.data:
            return jsonify({
                "success": False,
                "error": f"Video {video_id} not found"
            }), 404
        
        row = res.data[0]
        
        # Check if video is in uploaded or failed status
        if row.get("status") not in ["uploaded", "failed"]:
            return jsonify({
                "success": False,
                "error": f"Video {video_id} is not in uploaded or failed status"
            }), 400
        
        # Claim and process the video
        if not claim_video(db, video_id):
            return jsonify({
                "success": False,
                "error": f"Could not claim video {video_id} (may be processing by another worker)"
            }), 409
        
        start_time = datetime.now()
        try:
            process_one_video(db, s3, row)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            mark_status(db, video_id, "ready")
            
            return jsonify({
                "success": True,
                "message": f"Successfully processed video {video_id}",
                "duration_seconds": duration
            })
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"Error processing video {video_id}: {str(e)}")
            
            mark_status(db, video_id, "failed")
            
            return jsonify({
                "success": False,
                "error": str(e),
                "duration_seconds": duration
            }), 500
            
    except Exception as e:
        logger.error(f"Error in process_single_video: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)