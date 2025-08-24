import os
import sys
import logging
from datetime import datetime

# Add the parent directory to Python path so we can import from hoptix-flask
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Settings
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from worker.pipeline import fetch_one_uploaded_video, claim_video, process_one_video, mark_status
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_processing.log'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables with logging
try:
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_service_key = os.environ["SUPABASE_SERVICE_KEY"]
    aws_region = os.environ["AWS_REGION"]
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not openai_api_key:
        logger.warning("OPENAI_API_KEY not set - transcription will fail")
    else:
        logger.info("OpenAI API key found")

    logger.info(f"Loaded environment variables - AWS Region: {aws_region}")
except KeyError as e:
    logger.error(f"Missing required environment variable: {e}")
    sys.exit(1)

def main():
    logger.info("=== Starting batch video processing (process all 'uploaded') ===")
    start_time = datetime.now()

    succeeded = 0
    failed = 0
    processed_ids = []

    try:
        # Initialize connections
        logger.info("Initializing database and S3 connections...")
        settings = Settings()
        db = Supa(supabase_url, supabase_service_key)
        s3 = get_s3(aws_region)
        logger.info("Successfully connected to database and S3")

        # Drain the queue: repeatedly fetch one 'uploaded' until none remain
        while True:
            row = fetch_one_uploaded_video(db)
            if not row:
                logger.info("No more uploaded videos found in queue.")
                break

            vid = row["id"]
            s3_key = row.get("s3_key", "unknown")
            logger.info(f"Found video to process - ID: {vid}, S3 Key: {s3_key}")

            # Claim the video (best-effort compare-and-set)
            logger.info(f"Attempting to claim video {vid}...")
            if not claim_video(db, vid):
                logger.warning(f"Could not claim video {vid} (another worker may have taken it). Skipping.")
                continue
            logger.info(f"Successfully claimed video {vid}")

            # Process the video
            logger.info(f"Starting video processing for {vid}...")
            process_start = datetime.now()
            try:
                process_one_video(db, s3, row)  # Settings object is created inside the function
                process_end = datetime.now()
                process_duration = (process_end - process_start).total_seconds()

                mark_status(db, vid, "ready")
                succeeded += 1
                processed_ids.append(vid)
                logger.info(f"✅ Successfully processed video {vid} in {process_duration:.2f} seconds")

            except Exception as e:
                process_end = datetime.now()
                process_duration = (process_end - process_start).total_seconds()
                logger.error(
                    f"❌ Error processing video {vid} after {process_duration:.2f} seconds: {str(e)}",
                    exc_info=True
                )
                try:
                    mark_status(db, vid, "failed")
                    logger.info(f"Marked video {vid} as failed in database")
                except Exception as mark_error:
                    logger.error(f"Failed to mark video {vid} as failed: {str(mark_error)}")
                failed += 1

        logger.info(f"Batch complete. Succeeded: {succeeded}, Failed: {failed}, Total: {succeeded + failed}")
        if processed_ids:
            logger.info("Processed video IDs: " + ", ".join(processed_ids))

    except Exception as e:
        logger.error(f"Fatal error in main(): {str(e)}", exc_info=True)
        sys.exit(1)

    finally:
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        logger.info(f"=== Batch session completed in {total_duration:.2f} seconds ===")

if __name__ == "__main__":
    main()