import os
import sys
import logging
import tempfile
from datetime import datetime
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from tqdm import tqdm
import time
import random

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
    
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
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
            logger.info(f"🔧 Configured for parallel processing with {self.max_workers} workers")
        except KeyError as e:
            logger.error(f"Missing required environment variable: {e}")
            sys.exit(1)
    
    def _process_single_video(self, video_id: str, worker_id: str, db: Supa, gdrive: 'GoogleDriveClient', processing_service: 'ProcessingService', pbar: tqdm = None) -> dict:
        """Process a single video - designed to run in parallel worker thread"""
        result = {
            "video_id": video_id,
            "worker_id": worker_id,
            "success": False,
            "duration": 0,
            "error": None,
            "filename": ""
        }
        
        process_start = datetime.now()
        tmp_video_path = None
        
        try:
            # Fetch the video record
            video_result = db.client.table("videos").select(
                "id, s3_key, run_id, location_id, started_at, ended_at, meta"
            ).eq("id", video_id).limit(1).execute()
            
            if not video_result.data:
                raise Exception(f"Could not fetch video record")
                
            row = video_result.data[0]
            gdrive_file_id = row["meta"]["gdrive_file_id"]
            gdrive_file_name = row["meta"]["gdrive_file_name"]
            result["filename"] = gdrive_file_name

            if pbar:
                pbar.set_description(f"🔒 Worker-{worker_id}: Claiming {gdrive_file_name[:20]}...")

            # Claim the video (best-effort compare-and-set)
            if not claim_video(db, video_id):
                result["error"] = "Already processing"
                return result

            if pbar:
                pbar.set_description(f"⬇️ Worker-{worker_id}: Downloading {gdrive_file_name[:20]}...")

            # Download video temporarily from Google Drive for processing
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                tmp_video_path = tmp_file.name
            
            if gdrive.download_file(gdrive_file_id, tmp_video_path):
                if pbar:
                    pbar.set_description(f"🎬 Worker-{worker_id}: Processing {gdrive_file_name[:20]}...")
                
                # Process the video using our pipeline but with local file
                processing_service.process_video_from_local_file(row, tmp_video_path)
                
                process_end = datetime.now()
                result["duration"] = (process_end - process_start).total_seconds()

                mark_status(db, video_id, "ready")
                result["success"] = True
                
                if pbar:
                    pbar.set_description(f"✅ Worker-{worker_id}: Completed {gdrive_file_name[:20]}")
            else:
                raise Exception(f"Download failed")

        except Exception as e:
            process_end = datetime.now()
            result["duration"] = (process_end - process_start).total_seconds()
            result["error"] = str(e)
            
            if pbar:
                pbar.set_description(f"❌ Worker-{worker_id}: Failed {result['filename'][:20]}")
            
            try:
                mark_status(db, video_id, "failed")
            except Exception:
                pass  # Ignore marking errors for cleaner logs
                
        finally:
            # Always clean up temporary file
            if tmp_video_path:
                try:
                    os.remove(tmp_video_path)
                except Exception:
                    pass  # Ignore cleanup errors for cleaner logs
        
        return result
    
    def run(self, org_id: str, location_id: str, run_date: str):
        """Execute the full pipeline for the given org, location, and date."""
        print(f"\n🚀 Hoptix Video Processing Pipeline")
        print(f"{'='*50}")
        print(f"📅 Date: {run_date}")
        print(f"👥 Workers: {self.max_workers}")
        
        start_time = datetime.now()
        succeeded = 0
        failed = 0
        processed_ids = []

        try:
            # Initialize connections
            print(f"🔧 Initializing connections...")
            settings = Settings()
            db = Supa(self.supabase_url, self.supabase_service_key)
            s3 = get_s3(self.aws_region)
            folder_name = db.client.table("locations").select("name").eq("id", location_id).limit(1).execute().data[0]["name"]
            
            # Suppress verbose HTTP logs for cleaner output
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("googleapiclient").setLevel(logging.WARNING)
            logging.getLogger("google_auth_httplib2").setLevel(logging.WARNING)

            # Initialize services
            import_service = ImportService(db, settings, folder_name)
            processing_service = ProcessingService(db, settings)

            # Import videos from Google Drive
            print(f"📥 Importing videos from Google Drive for {folder_name}...")
            imported_video_ids = import_service.import_videos_from_gdrive(s3, org_id, location_id, run_date)
            
            if not imported_video_ids:
                print(f"ℹ️  No videos found for {run_date}")
                return

            print(f"✅ Found {len(imported_video_ids)} videos to process")

            # Process videos in parallel using ThreadPoolExecutor
            gdrive = GoogleDriveClient()
            
            with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="VideoWorker") as executor:
                # Create progress bar
                with tqdm(total=len(imported_video_ids), desc="🎬 Processing videos", 
                         bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                         ncols=100) as pbar:
                    
                    # Submit all videos for processing with staggered start
                    future_to_video = {}
                    for i, vid in enumerate(imported_video_ids):
                        worker_id = f"{i % self.max_workers + 1:02d}"
                        future = executor.submit(self._process_single_video, vid, worker_id, db, gdrive, processing_service, pbar)
                        future_to_video[future] = vid
                        
                        # Add small delay between submissions to avoid overwhelming Google Drive
                        if i < len(imported_video_ids) - 1:  # Don't delay after last submission
                            time.sleep(random.uniform(0.1, 0.5))
                    
                    # Collect results as they complete
                    for future in as_completed(future_to_video):
                        vid = future_to_video[future]
                        try:
                            result = future.result()
                            if result["success"]:
                                succeeded += 1
                                processed_ids.append(vid)
                                pbar.set_postfix_str(f"✅ {result['filename'][:25]} ({result['duration']:.1f}s)")
                            else:
                                failed += 1
                                pbar.set_postfix_str(f"❌ {result.get('filename', 'Unknown')[:25]} - {result.get('error', 'Failed')}")
                        except Exception as exc:
                            failed += 1
                            pbar.set_postfix_str(f"💥 Exception: {str(exc)[:30]}")
                        
                        pbar.update(1)

            # Final summary
            total_duration = (datetime.now() - start_time).total_seconds()
            print(f"\n📊 Processing Summary:")
            print(f"{'='*50}")
            print(f"✅ Successful: {succeeded}")
            print(f"❌ Failed: {failed}")
            print(f"⏱️  Total time: {total_duration:.1f}s")
            print(f"📈 Average: {total_duration/(succeeded+failed):.1f}s per video")
            
            if succeeded > 0:
                success_rate = (succeeded / (succeeded + failed)) * 100
                print(f"🎯 Success rate: {success_rate:.1f}%")

        except Exception as e:
            print(f"\n💀 Fatal error: {str(e)}")
            logger.error(f"Fatal error in main(): {str(e)}", exc_info=True)
            sys.exit(1)

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
    parser.add_argument('--workers', type=int, default=10,
                       help='Number of parallel workers for video processing (default: 10)')
    
    args = parser.parse_args()
    
    command = FullPipelineCommand(max_workers=args.workers)
    command.run(args.org_id, args.location_id, args.date)

if __name__ == "__main__":
    main()
