import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List
from integrations.db_supabase import Supa
from integrations.gdrive_client import GoogleDriveClient, parse_timestamp_from_filename
from config import Settings
from .database_service import DatabaseService
from .video_service import VideoService

logger = logging.getLogger(__name__)

class ImportService:
    """Google Drive video import operations."""
    
    def __init__(self, db: Supa, settings: Settings, folder_name: str):
        self.db = db
        self.settings = settings
        self.database_service = DatabaseService(db)
        self.video_service = VideoService()
        
        # Configuration for Google Drive
        self.SHARED_DRIVE_NAME = "Hoptix Video Server"
        self.FOLDER_NAME = folder_name
        self.S3_PREFIX = os.getenv("S3_PREFIX", f"gdrive/{folder_name}")
        self.DEFAULT_DURATION_SEC = int(os.getenv("GDRIVE_VIDEO_DURATION_SEC", "3600"))  # 1 hour default
    
    def import_videos_from_gdrive(self, s3, org_id: str, location_id: str, run_date: str) -> List[str]:
        """Import videos from Google Drive for the specified date and return video IDs"""
        logger.info(f"Starting Google Drive import for date: {run_date}")
        
        # Initialize Google Drive client
        gdrive = GoogleDriveClient()
        
        # Find shared drive
        drive_id = gdrive.find_shared_drive(self.SHARED_DRIVE_NAME)
        if not drive_id:
            raise Exception(f"Shared drive '{self.SHARED_DRIVE_NAME}' not found")
        
        # Find folder
        folder_id = gdrive.find_folder_in_drive(drive_id, self.FOLDER_NAME)
        if not folder_id:
            raise Exception(f"Folder '{self.FOLDER_NAME}' not found")
        
        # List and filter video files
        video_files = gdrive.list_video_files(folder_id, drive_id)
        video_files = self.video_service.filter_videos_by_date(video_files, run_date)
        
        if not video_files:
            logger.warning(f"No video files found for date: {run_date}")
            return []
        
        logger.info(f"Found {len(video_files)} video files for date {run_date}")
        
        # Create run for the provided org and location
        run_id = self.database_service.create_run_for_date(org_id, location_id, run_date)
        
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
            ended_at = started_at + timedelta(seconds=self.DEFAULT_DURATION_SEC)
            
            # Generate a placeholder S3 key (not actually used for storage)
            file_basename = os.path.splitext(file_info['name'])[0]
            s3_key = f"{self.S3_PREFIX}/{file_basename}.mp4"
            
            logger.info(f"Processing video directly from Google Drive: {file_info['name']}")
            
            # Import to database
            video_data = {
                "id": video_id,
                "run_id": run_id,
                "location_id": location_id,
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
            existing = self.db.client.table("videos").select("id").eq("s3_key", s3_key).limit(1).execute()
            
            if existing.data:
                # Video already exists, use existing ID
                existing_video_id = existing.data[0]["id"]
                imported_video_ids.append(existing_video_id)
                logger.info(f"Video already exists with ID {existing_video_id}: {file_info['name']}")
            else:
                # Insert new video
                self.db.client.table("videos").upsert(video_data, on_conflict="id").execute()
                imported_video_ids.append(video_id)
                logger.info(f"Imported new video {video_id}: {file_info['name']}")
        
        logger.info(f"Successfully imported {len(imported_video_ids)} videos from Google Drive")
        return imported_video_ids
