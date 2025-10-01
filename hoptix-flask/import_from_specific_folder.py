#!/usr/bin/env python3
"""
Import videos directly from a specific Google Drive folder ID
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrations.gdrive_client import GoogleDriveClient
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from config import Settings
from services.import_service import ImportService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_from_folder_id(folder_id: str, org_id: str, location_id: str, run_date: str):
    """Import videos directly from a specific Google Drive folder ID"""
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize services
        logger.info("🔧 Initializing services...")
        settings = Settings()
        db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        s3 = get_s3(settings.AWS_REGION)
        gdrive = GoogleDriveClient()
        
        logger.info("✅ Services initialized successfully")
        
        # Get folder information
        logger.info(f"🔍 Getting folder information for ID: {folder_id}")
        folder_info = gdrive.get_file_info(folder_id)
        
        if not folder_info:
            logger.error(f"❌ Could not get folder information for ID: {folder_id}")
            return
        
        folder_name = folder_info.get('name', 'Unknown Folder')
        logger.info(f"📁 Folder name: {folder_name}")
        
        # List all video files in the specific folder
        logger.info(f"📁 Listing all video files in folder '{folder_name}'...")
        video_files = gdrive.list_video_files_shared_with_me(folder_id)
        
        if not video_files:
            logger.warning(f"⚠️ No video files found in folder '{folder_name}'")
            return
        
        logger.info(f"✅ Found {len(video_files)} video files:")
        
        # Show the files that will be imported
        for i, file_info in enumerate(video_files[:10], 1):  # Show first 10
            file_name = file_info.get('name', 'Unknown Name')
            file_size = file_info.get('size', 0)
            
            # Convert size to human readable format
            if file_size:
                try:
                    file_size = int(file_size)
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    elif file_size < 1024 * 1024 * 1024:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"
                except (ValueError, TypeError):
                    size_str = "Unknown size"
            else:
                size_str = "Unknown size"
            
            logger.info(f"  {i:2d}. 📄 {file_name} ({size_str})")
        
        if len(video_files) > 10:
            logger.info(f"  ... and {len(video_files) - 10} more files")
        
        # Create a custom import service that uses the specific folder ID
        logger.info("🔧 Creating custom import service...")
        
        # Create run for the provided org and location
        from services.database_service import DatabaseService
        database_service = DatabaseService(db)
        run_id = database_service.create_run_for_date(org_id, location_id, run_date)
        logger.info(f"✅ Created run with ID: {run_id}")
        
        imported_video_ids = []
        
        for i, file_info in enumerate(video_files, 1):
            logger.info(f"Processing file {i}/{len(video_files)}: {file_info['name']}")
            
            import uuid
            video_id = str(uuid.uuid4())
            
            # Parse timestamp from filename
            from integrations.gdrive_client import parse_timestamp_from_filename
            started_at = parse_timestamp_from_filename(file_info['name'])
            if started_at is None:
                logger.warning(f"Could not parse timestamp from '{file_info['name']}', using current time")
                from datetime import datetime, timezone
                started_at = datetime.now(timezone.utc)
            
            # Calculate end time (assume 1 hour duration by default)
            from datetime import timedelta
            ended_at = started_at + timedelta(seconds=3600)  # 1 hour default
            
            # Generate S3 key
            file_basename = os.path.splitext(file_info['name'])[0]
            original_ext = os.path.splitext(file_info['name'])[1] or '.avi'
            s3_key = f"gdrive/{folder_name}/{file_basename}{original_ext}"
            
            logger.info(f"📎 Original file extension: {original_ext}")
            logger.info(f"🗂️ Generated S3 key: {s3_key}")
            
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
                    "source": "google_drive_specific_folder",
                    "gdrive_file_id": file_info['id'],
                    "gdrive_file_name": file_info['name'],
                    "gdrive_folder_id": folder_id,
                    "gdrive_folder_name": folder_name,
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
                try:
                    db.client.table("videos").upsert(video_data, on_conflict="id").execute()
                    imported_video_ids.append(video_id)
                    logger.info(f"✅ Successfully imported new video {video_id}: {file_info['name']}")
                    
                    # Verify the video was inserted with correct status
                    verify_result = db.client.table("videos").select("id, status").eq("id", video_id).execute()
                    if verify_result.data:
                        actual_status = verify_result.data[0]["status"]
                        logger.info(f"🔍 Verified video {video_id} status: {actual_status}")
                    else:
                        logger.error(f"❌ Could not verify video {video_id} was inserted")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to import video {video_id}: {e}")
                    # Try to insert with failed status
                    video_data["status"] = "failed"
                    try:
                        db.client.table("videos").upsert(video_data, on_conflict="id").execute()
                        logger.info(f"📝 Marked video {video_id} as failed due to import error")
                    except Exception as e2:
                        logger.error(f"❌ Could not even mark video as failed: {e2}")
        
        logger.info(f"✅ Successfully imported {len(imported_video_ids)} videos from folder '{folder_name}'")
        logger.info(f"📊 Import summary:")
        logger.info(f"   - Total files found: {len(video_files)}")
        logger.info(f"   - Videos imported: {len(imported_video_ids)}")
        logger.info(f"   - Run ID: {run_id}")
        logger.info(f"   - Organization ID: {org_id}")
        logger.info(f"   - Location ID: {location_id}")
        logger.info(f"   - Date: {run_date}")
        
        return imported_video_ids
        
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # Configuration - you can modify these values
    FOLDER_ID = "1d997vkf7a6b7wVJxcC99wQY4ZWIQ8QOX"  # From your Google Drive link
    ORG_ID = "your-org-id"  # Replace with actual org ID
    LOCATION_ID = "your-location-id"  # Replace with actual location ID
    RUN_DATE = "2025-07-15"  # Replace with desired date (YYYY-MM-DD format)
    
    logger.info(f"🚀 Starting import from Google Drive folder: {FOLDER_ID}")
    logger.info(f"📅 Date: {RUN_DATE}")
    logger.info(f"🏢 Org ID: {ORG_ID}")
    logger.info(f"📍 Location ID: {LOCATION_ID}")
    
    imported_ids = import_from_folder_id(FOLDER_ID, ORG_ID, LOCATION_ID, RUN_DATE)
    
    if imported_ids:
        logger.info(f"🎉 Import completed successfully! {len(imported_ids)} videos imported.")
    else:
        logger.error("❌ Import failed or no videos were imported.")
