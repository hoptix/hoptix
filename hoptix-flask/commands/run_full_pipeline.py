import os
import sys
import logging
import tempfile
from datetime import datetime
from typing import List

# Add the parent directory to Python path so we can import from hoptix-flask
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Settings
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from integrations.gdrive_client import GoogleDriveClient
from worker.pipeline import claim_video, mark_status
from services.import_service import ImportService
from services.processing_service import ProcessingService
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class FullPipelineCommand:
    """End-to-end command to import videos from Google Drive and process them."""
    
    def __init__(self):
        load_dotenv()
        
        # Environment variables with logging
        try:
            self.supabase_url = os.environ["SUPABASE_URL"]
            self.supabase_service_key = os.environ["SUPABASE_SERVICE_KEY"]
            self.aws_region = os.environ["AWS_REGION"]
            openai_api_key = os.environ.get("OPENAI_API_KEY")

            if not openai_api_key:
                logger.warning("OPENAI_API_KEY not set - transcription will fail")
            else:
                logger.info("OpenAI API key found")

            logger.info(f"Loaded environment variables - AWS Region: {self.aws_region}")
        except KeyError as e:
            logger.error(f"Missing required environment variable: {e}")
            sys.exit(1)
    
    def run(self, org_id: str, location_id: str, run_date: str):
        """Execute the full pipeline for the given org, location, and date."""
        logger.info(f"=== Starting Google Drive import and processing ===")
        logger.info(f"Organization ID: {org_id}")
        logger.info(f"Location ID: {location_id}")
        logger.info(f"Date: {run_date}")
        start_time = datetime.now()

        succeeded = 0
        failed = 0
        processed_ids = []

        try:
            # Initialize connections
            logger.info("Initializing database and S3 connections...")
            settings = Settings()
            db = Supa(self.supabase_url, self.supabase_service_key)
            s3 = get_s3(self.aws_region)
            logger.info("Successfully connected to database and S3")

            # Initialize services
            import_service = ImportService(db, settings)
            processing_service = ProcessingService(db, settings)

            # Import videos from Google Drive
            logger.info(f"Importing videos from Google Drive for org: {org_id}, location: {location_id}, date: {run_date}")
            imported_video_ids = import_service.import_videos_from_gdrive(s3, org_id, location_id, run_date)
            
            if not imported_video_ids:
                logger.info("No videos imported from Google Drive. Nothing to process.")
                return

            logger.info(f"Imported {len(imported_video_ids)} videos. Starting processing...")

            # Process each imported video directly from Google Drive
            gdrive = GoogleDriveClient()  # Reuse the authenticated client
            
            for vid in imported_video_ids:
                logger.info(f"Processing imported video: {vid}")
                
                # Fetch the video record
                video_result = db.client.table("videos").select(
                    "id, s3_key, run_id, location_id, started_at, ended_at, meta"
                ).eq("id", vid).limit(1).execute()
                
                if not video_result.data:
                    logger.error(f"Could not fetch video record for {vid}")
                    failed += 1
                    continue
                    
                row = video_result.data[0]
                gdrive_file_id = row["meta"]["gdrive_file_id"]
                gdrive_file_name = row["meta"]["gdrive_file_name"]
                logger.info(f"Found video to process - ID: {vid}, Google Drive file: {gdrive_file_name}")

                # Claim the video (best-effort compare-and-set)
                logger.info(f"Attempting to claim video {vid}...")
                if not claim_video(db, vid):
                    logger.warning(f"Could not claim video {vid} (may already be processing). Skipping.")
                    continue
                logger.info(f"Successfully claimed video {vid}")

                # Process the video directly from Google Drive
                logger.info(f"Starting video processing for {vid}...")
                process_start = datetime.now()
                
                # Download video temporarily from Google Drive for processing
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                    tmp_video_path = tmp_file.name
                
                try:
                    logger.info(f"Downloading video from Google Drive for processing...")
                    if gdrive.download_file(gdrive_file_id, tmp_video_path):
                        # Process the video using our pipeline but with local file
                        processing_service.process_video_from_local_file(row, tmp_video_path)
                        
                        process_end = datetime.now()
                        process_duration = (process_end - process_start).total_seconds()

                        mark_status(db, vid, "ready")
                        succeeded += 1
                        processed_ids.append(vid)
                        logger.info(f"✅ Successfully processed video {vid} in {process_duration:.2f} seconds")
                    else:
                        logger.error(f"Failed to download video {gdrive_file_name} from Google Drive")
                        failed += 1

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
                finally:
                    # Always clean up temporary file, even if processing failed
                    try:
                        os.remove(tmp_video_path)
                        logger.debug(f"Cleaned up temporary file: {tmp_video_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")

            logger.info(f"Batch complete. Succeeded: {succeeded}, Failed: {failed}, Total: {succeeded + failed}")
            if processed_ids:
                logger.info("Processed video IDs: " + ", ".join(processed_ids))

        except Exception as e:
            logger.error(f"Fatal error in main(): {str(e)}", exc_info=True)
            sys.exit(1)

        finally:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            logger.info(f"=== Session completed in {total_duration:.2f} seconds ===")

def main():
    """Main entry point for the full pipeline command."""
    import argparse
    
    # Configure logging for production - only to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    parser = argparse.ArgumentParser(
        description='Import videos from Google Drive for a specific organization, location, and date',
        epilog='Example: python commands/run_full_pipeline.py --org-id abc123 --location-id def456 --date 2025-08-29'
    )
    parser.add_argument('--org-id', type=str, required=True,
                       help='Organization ID (required) - must exist in database')
    parser.add_argument('--location-id', type=str, required=True,
                       help='Location ID (required) - must exist in database and belong to the organization')
    parser.add_argument('--date', type=str, required=True,
                       help='Date in YYYY-MM-DD format (required) - import and process videos from this date')
    
    args = parser.parse_args()
    
    command = FullPipelineCommand()
    command.run(args.org_id, args.location_id, args.date)

if __name__ == "__main__":
    main()
