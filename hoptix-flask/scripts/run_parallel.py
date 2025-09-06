import os
import sys
import logging
import argparse
import tempfile
import multiprocessing
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed
import queue
import threading

# Add the parent directory to Python path so we can import from hoptix-flask
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Settings
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from integrations.gdrive_client import GoogleDriveClient, parse_timestamp_from_filename
from worker.pipeline import claim_video, mark_status
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parallel_video_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
try:
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_service_key = os.environ["SUPABASE_SERVICE_KEY"]
    aws_region = os.environ["AWS_REGION"]
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not openai_api_key:
        logger.warning("OPENAI_API_KEY not set - transcription will fail")

    logger.info(f"Loaded environment variables - AWS Region: {aws_region}")
except KeyError as e:
    logger.error(f"Missing required environment variable: {e}")
    sys.exit(1)

# Configuration for Google Drive
SHARED_DRIVE_NAME = "Hoptix Video Server"
FOLDER_NAME = "DQ Cary"
S3_PREFIX = os.getenv("S3_PREFIX", "gdrive/dq_cary")
DEFAULT_DURATION_SEC = int(os.getenv("GDRIVE_VIDEO_DURATION_SEC", "3600"))

def setup_database_entities(db: Supa):
    """Setup org, location entities for DQ Cary"""
    import uuid
    
    # Generate IDs
    org_id = str(uuid.uuid4())
    loc_id = str(uuid.uuid4())
    
    # Upsert org
    org_data = {"id": org_id, "name": "Dairy Queen"}
    db.client.table("orgs").upsert(org_data, on_conflict="id").execute()
    
    # Upsert location  
    loc_data = {
        "id": loc_id,
        "org_id": org_id,
        "name": "Cary",
        "tz": "America/New_York"
    }
    db.client.table("locations").upsert(loc_data, on_conflict="id").execute()
    
    logger.info(f"Setup org_id: {org_id}, loc_id: {loc_id}")
    return org_id, loc_id

def create_run_for_date(db: Supa, org_id: str, loc_id: str, run_date: str) -> str:
    """Create or get run for specific date"""
    import uuid
    
    # Try to find existing run for this date and location
    existing = db.client.table("runs").select("id").eq(
        "location_id", loc_id
    ).eq("run_date", run_date).limit(1).execute()
    
    if existing.data:
        run_id = existing.data[0]["id"]
        logger.info(f"Using existing run_id: {run_id} for date: {run_date}")
    else:
        run_id = str(uuid.uuid4())
        run_data = {
            "id": run_id,
            "org_id": org_id,
            "location_id": loc_id,
            "run_date": run_date,
            "status": "uploaded"
        }
        db.client.table("runs").upsert(run_data, on_conflict="id").execute()
        logger.info(f"Created new run_id: {run_id} for date: {run_date}")
    
    return run_id

def filter_videos_by_date(video_files: List, target_date: str) -> List:
    """Filter video files to only include those matching the target date"""
    from dateutil import parser as dateparse
    
    target_date_obj = dateparse.parse(target_date).date()
    filtered_files = []
    
    for file_info in video_files:
        # Try to parse date from filename
        video_timestamp = parse_timestamp_from_filename(file_info['name'])
        
        if video_timestamp:
            video_date = video_timestamp.date()
            if video_date == target_date_obj:
                filtered_files.append(file_info)
                logger.debug(f"Including {file_info['name']} (date: {video_date})")
            else:
                logger.debug(f"Skipping {file_info['name']} (date: {video_date}, target: {target_date_obj})")
        else:
            logger.warning(f"Skipping {file_info['name']} (could not parse date from filename)")
    
    return filtered_files

def import_videos_from_gdrive(db: Supa, s3, settings: Settings, run_date: str) -> List[str]:
    """Import videos from Google Drive for the specified date and return video IDs"""
    import uuid
    from dateutil import parser as dateparse
    
    logger.info(f"Starting Google Drive import for date: {run_date}")
    
    # Initialize Google Drive client
    gdrive = GoogleDriveClient()
    
    # Find shared drive
    drive_id = gdrive.find_shared_drive(SHARED_DRIVE_NAME)
    if not drive_id:
        raise Exception(f"Shared drive '{SHARED_DRIVE_NAME}' not found")
    
    # Find folder
    folder_id = gdrive.find_folder_in_drive(drive_id, FOLDER_NAME)
    if not folder_id:
        raise Exception(f"Folder '{FOLDER_NAME}' not found")
    
    # List and filter video files
    video_files = gdrive.list_video_files(folder_id, drive_id)
    video_files = filter_videos_by_date(video_files, run_date)
    
    if not video_files:
        logger.warning(f"No video files found for date: {run_date}")
        return []
    
    logger.info(f"Found {len(video_files)} video files for date {run_date}")
    
    # Setup database entities
    org_id, loc_id = setup_database_entities(db)
    run_id = create_run_for_date(db, org_id, loc_id, run_date)
    
    imported_video_ids = []
    
    for i, file_info in enumerate(video_files, 1):
        logger.info(f"Processing file {i}/{len(video_files)}: {file_info['name']}")
        
        video_id = str(uuid.uuid4())
        
        # Parse timestamp from filename
        started_at = parse_timestamp_from_filename(file_info['name'])
        if started_at is None:
            logger.warning(f"Could not parse timestamp from '{file_info['name']}', using current time")
            started_at = datetime.now(timezone.utc)
        
        # Calculate end time (assume 1 hour duration by default)
        ended_at = started_at + timedelta(seconds=DEFAULT_DURATION_SEC)
        
        # Generate a placeholder S3 key (not actually used for storage)
        file_basename = os.path.splitext(file_info['name'])[0]
        s3_key = f"{S3_PREFIX}/{file_basename}.mp4"
        
        # Import to database
        video_data = {
            "id": video_id,
            "run_id": run_id,
            "location_id": loc_id,
            "camera_id": f"gdrive-cam-{file_info['id'][:8]}",
            "s3_key": s3_key,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "status": "uploaded",
            "meta": {
                "source": "google_drive",
                "gdrive_file_id": file_info['id'],
                "gdrive_file_name": file_info['name'],
                "file_size": file_info.get('size', 0)
            }
        }
        
        # Check if video already exists by s3_key
        existing = db.client.table("videos").select("id").eq("s3_key", s3_key).limit(1).execute()
        
        if existing.data:
            # Video already exists, use existing ID
            existing_video_id = existing.data[0]["id"]
            imported_video_ids.append(existing_video_id)
            logger.info(f"Video already exists with ID {existing_video_id}: {file_info['name']}")
        else:
            # Insert new video
            db.client.table("videos").upsert(video_data, on_conflict="id").execute()
            imported_video_ids.append(video_id)
            logger.info(f"Imported new video {video_id}: {file_info['name']}")
    
    logger.info(f"Successfully imported {len(imported_video_ids)} videos from Google Drive")
    return imported_video_ids

def process_video_worker(video_id: str) -> Dict:
    """Worker function to process a single video - runs in separate process"""
    from worker.adapter import transcribe_video, split_into_transactions, grade_transactions
    from worker.pipeline import insert_transactions, upsert_grades
    from integrations.s3_client import put_jsonl
    
    worker_logger = logging.getLogger(f"worker-{os.getpid()}")
    
    try:
        # Initialize connections in worker process
        settings = Settings()
        db = Supa(supabase_url, supabase_service_key)
        s3 = get_s3(aws_region)
        gdrive = GoogleDriveClient()
        
        worker_logger.info(f"Worker {os.getpid()} processing video: {video_id}")
        
        # Fetch the video record
        video_result = db.client.table("videos").select(
            "id, s3_key, run_id, location_id, started_at, ended_at, meta"
        ).eq("id", video_id).limit(1).execute()
        
        if not video_result.data:
            return {"video_id": video_id, "status": "error", "error": "Video record not found"}
        
        row = video_result.data[0]
        gdrive_file_id = row["meta"]["gdrive_file_id"]
        gdrive_file_name = row["meta"]["gdrive_file_name"]
        
        # Claim the video
        if not claim_video(db, video_id):
            return {"video_id": video_id, "status": "skipped", "error": "Could not claim video (already processing)"}
        
        start_time = datetime.now()
        
        # Download video temporarily from Google Drive for processing
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
            tmp_video_path = tmp_file.name
        
        try:
            worker_logger.info(f"Downloading {gdrive_file_name} from Google Drive...")
            if not gdrive.download_file(gdrive_file_id, tmp_video_path):
                return {"video_id": video_id, "status": "error", "error": "Failed to download from Google Drive"}
            
            # Process the video
            worker_logger.info(f"Starting processing pipeline for {video_id}...")
            
            # 1) ASR segments
            segments = transcribe_video(tmp_video_path)
            worker_logger.info(f"Transcription completed: {len(segments)} segments")

            # 2) Split into transactions
            txs = split_into_transactions(segments, row["started_at"], row.get("s3_key"))
            worker_logger.info(f"Transaction splitting completed: {len(txs)} transactions")

            # 3) Upload artifacts to S3
            prefix = f'deriv/session={video_id}/'
            put_jsonl(s3, settings.DERIV_BUCKET, prefix + "segments.jsonl", segments)
            put_jsonl(s3, settings.DERIV_BUCKET, prefix + "transactions.jsonl", txs)

            # 4) Persist transactions
            tx_ids = insert_transactions(db, row, txs)
            worker_logger.info(f"Inserted {len(tx_ids)} transactions")

            # 5) Grade transactions
            grades = grade_transactions(txs)
            put_jsonl(s3, settings.DERIV_BUCKET, prefix + "grades.jsonl", grades)

            # 6) Upsert grades
            upsert_grades(db, tx_ids, grades)
            
            # Mark as ready
            mark_status(db, video_id, "ready")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            worker_logger.info(f"✅ Successfully processed {video_id} in {duration:.2f}s")
            return {"video_id": video_id, "status": "success", "duration": duration}
            
        finally:
            # Always clean up temporary file
            try:
                os.remove(tmp_video_path)
                worker_logger.debug(f"Cleaned up temporary file: {tmp_video_path}")
            except Exception as cleanup_error:
                worker_logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
                
    except Exception as e:
        worker_logger.error(f"❌ Error processing video {video_id}: {str(e)}", exc_info=True)
        try:
            mark_status(db, video_id, "failed")
        except:
            pass
        return {"video_id": video_id, "status": "error", "error": str(e)}

def main():
    parser = argparse.ArgumentParser(
        description='Import and process videos from Google Drive in parallel',
        epilog='Example: python scripts/run_parallel.py --date 2025-08-29 --workers 8'
    )
    parser.add_argument('--date', type=str, required=True,
                       help='Date in YYYY-MM-DD format (required)')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of parallel workers (default: 4)')
    
    args = parser.parse_args()
    run_date = args.date
    num_workers = args.workers
    
    logger.info(f"=== Starting parallel Google Drive processing ===")
    logger.info(f"📅 Date: {run_date}")
    logger.info(f"👥 Workers: {num_workers}")
    
    start_time = datetime.now()
    
    try:
        # Initialize connections
        settings = Settings()
        db = Supa(supabase_url, supabase_service_key)
        s3 = get_s3(aws_region)
        
        # Import videos from Google Drive
        logger.info(f"Importing videos from Google Drive for date: {run_date}")
        imported_video_ids = import_videos_from_gdrive(db, s3, settings, run_date)
        
        if not imported_video_ids:
            logger.info("No videos imported from Google Drive. Nothing to process.")
            return
        
        logger.info(f"📥 Imported {len(imported_video_ids)} videos")
        logger.info(f"🚀 Starting parallel processing with {num_workers} workers...")
        
        # Process videos in parallel
        succeeded = 0
        failed = 0
        skipped = 0
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all jobs
            future_to_video = {
                executor.submit(process_video_worker, video_id): video_id 
                for video_id in imported_video_ids
            }
            
            # Process results as they complete
            for future in as_completed(future_to_video):
                video_id = future_to_video[future]
                try:
                    result = future.result()
                    status = result["status"]
                    
                    if status == "success":
                        succeeded += 1
                        duration = result.get("duration", 0)
                        logger.info(f"✅ {video_id} completed in {duration:.2f}s")
                    elif status == "skipped":
                        skipped += 1
                        logger.warning(f"⏭️  {video_id} skipped: {result.get('error', 'Unknown')}")
                    else:
                        failed += 1
                        error = result.get("error", "Unknown error")
                        logger.error(f"❌ {video_id} failed: {error}")
                        
                except Exception as exc:
                    failed += 1
                    logger.error(f"❌ {video_id} generated an exception: {exc}")
        
        # Final summary
        total = succeeded + failed + skipped
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        logger.info(f"")
        logger.info(f"=== PROCESSING COMPLETE ===")
        logger.info(f"✅ Succeeded: {succeeded}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⏭️  Skipped: {skipped}")
        logger.info(f"📊 Total: {total}")
        logger.info(f"⏱️  Total time: {total_duration:.2f}s")
        if succeeded > 0:
            logger.info(f"⚡ Average per video: {total_duration/succeeded:.2f}s")
        
    except Exception as e:
        logger.error(f"Fatal error in main(): {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
