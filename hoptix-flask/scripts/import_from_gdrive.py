#!/usr/bin/env python3
"""
Import videos from Google Drive shared drive to Hoptix system.

This script:
1. Connects to Google Drive API
2. Finds the 'Hoptix Video Server' shared drive
3. Locates the 'DQ Cary' folder
4. Lists video files and imports them to the database
5. Optionally downloads videos to S3 for processing

Usage:
    python scripts/import_from_gdrive.py [--download-to-s3] [--run-date YYYY-MM-DD]
"""

import os
import sys
import uuid
import argparse
import datetime as dt
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.gdrive_client import GoogleDriveClient, parse_timestamp_from_filename
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3, put_file
import tempfile

load_dotenv()

# Configuration
SHARED_DRIVE_NAME = "Hoptix Video Server"
FOLDER_NAME = "DQ Cary"
S3_PREFIX = os.getenv("S3_PREFIX", "gdrive/dq_cary")
DEFAULT_DURATION_SEC = int(os.getenv("GDRIVE_VIDEO_DURATION_SEC", "3600"))  # 1 hour default

def setup_database_entities():
    """Setup org, location, and run entities for DQ Cary"""
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    db = Supa(supabase_url, supabase_key)
    
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
    
    print(f"✅ Setup org_id: {org_id}")
    print(f"✅ Setup loc_id: {loc_id}")
    
    return db, org_id, loc_id

def create_run_for_date(db: Supa, org_id: str, loc_id: str, run_date: str) -> str:
    """Create or get run for specific date"""
    run_id = str(uuid.uuid4())
    
    run_data = {
        "id": run_id,
        "org_id": org_id,
        "location_id": loc_id,
        "run_date": run_date,
        "status": "uploaded"
    }
    
    # Try to find existing run for this date and location
    existing = db.client.table("runs").select("id").eq(
        "location_id", loc_id
    ).eq("run_date", run_date).limit(1).execute()
    
    if existing.data:
        run_id = existing.data[0]["id"]
        print(f"📋 Using existing run_id: {run_id} for date: {run_date}")
    else:
        db.client.table("runs").upsert(run_data, on_conflict="id").execute()
        print(f"✅ Created new run_id: {run_id} for date: {run_date}")
    
    return run_id

def filter_videos_by_date(video_files: List[Dict], target_date: str) -> List[Dict]:
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
                print(f"✅ Including {file_info['name']} (date: {video_date})")
            else:
                print(f"⏭️  Skipping {file_info['name']} (date: {video_date}, target: {target_date_obj})")
        else:
            print(f"⚠️  Skipping {file_info['name']} (could not parse date from filename)")
    
    return filtered_files

def import_video_to_db(db: Supa, loc_id: str, run_id: str, file_info: Dict, 
                       s3_key: Optional[str] = None) -> str:
    """Import a video file record to the database"""
    
    video_id = str(uuid.uuid4())
    
    # Try to parse timestamp from filename
    started_at = parse_timestamp_from_filename(file_info['name'])
    
    if started_at is None:
        # Fallback to file creation time if available
        if 'createdTime' in file_info:
            from dateutil import parser as dateparse
            started_at = dateparse.isoparse(file_info['createdTime'])
        else:
            # Last resort: use current time
            started_at = dt.datetime.now(dt.timezone.utc)
            print(f"⚠️  Could not parse timestamp from '{file_info['name']}', using current time")
    
    # Calculate end time (assume 1 hour duration by default)
    ended_at = started_at + dt.timedelta(seconds=DEFAULT_DURATION_SEC)
    
    # Generate S3 key if not provided
    if s3_key is None:
        file_basename = os.path.splitext(file_info['name'])[0]
        s3_key = f"{S3_PREFIX}/{file_basename}.mp4"
    
    video_data = {
        "id": video_id,
        "run_id": run_id,
        "location_id": loc_id,
        "camera_id": f"gdrive-cam-{file_info['id'][:8]}",  # Use part of file ID as camera ID
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
    
    db.client.table("videos").upsert(video_data, on_conflict="id").execute()
    
    print(f"📹 Imported video: {file_info['name']}")
    print(f"   video_id: {video_id}")
    print(f"   started_at: {started_at.isoformat()}")
    print(f"   s3_key: {s3_key}")
    
    return video_id

def download_to_s3(gdrive: GoogleDriveClient, s3, bucket: str, file_info: Dict, s3_key: str) -> bool:
    """Download file from Google Drive and upload to S3"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.tmp') as tmp_file:
            print(f"📥 Downloading {file_info['name']} from Google Drive...")
            
            if not gdrive.download_file(file_info['id'], tmp_file.name):
                return False
            
            print(f"📤 Uploading to S3: {s3_key}")
            put_file(s3, bucket, s3_key, tmp_file.name, content_type="video/mp4")
            
            print(f"✅ Successfully uploaded to S3: {s3_key}")
            return True
            
    except Exception as e:
        print(f"❌ Error downloading/uploading {file_info['name']}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Import videos from Google Drive for a specific date',
        epilog='Example: python scripts/import_from_gdrive.py --run-date 2025-08-29 --download-to-s3'
    )
    parser.add_argument('--download-to-s3', action='store_true', 
                       help='Download videos to S3 (requires S3 credentials)')
    parser.add_argument('--run-date', type=str, required=True,
                       help='Run date in YYYY-MM-DD format (required) - only videos from this date will be imported')
    parser.add_argument('--max-files', type=int, default=None,
                       help='Maximum number of files to import (for testing)')
    
    args = parser.parse_args()
    
    run_date = args.run_date
    
    print(f"🚀 Starting Google Drive import for run date: {run_date}")
    
    try:
        # Initialize Google Drive client
        print("🔐 Authenticating with Google Drive...")
        gdrive = GoogleDriveClient()
        
        # Find shared drive
        print(f"🔍 Finding shared drive: {SHARED_DRIVE_NAME}")
        drive_id = gdrive.find_shared_drive(SHARED_DRIVE_NAME)
        if not drive_id:
            print(f"❌ Shared drive '{SHARED_DRIVE_NAME}' not found")
            return 1
        
        # Find folder
        print(f"📁 Finding folder: {FOLDER_NAME}")
        folder_id = gdrive.find_folder_in_drive(drive_id, FOLDER_NAME)
        if not folder_id:
            print(f"❌ Folder '{FOLDER_NAME}' not found")
            return 1
        
        # List video files
        print("📋 Listing video files...")
        video_files = gdrive.list_video_files(folder_id, drive_id)
        
        if not video_files:
            print("ℹ️  No video files found")
            return 0
        
        print(f"📊 Found {len(video_files)} video files total")
        
        # Filter videos by date
        print(f"🔍 Filtering videos for date: {run_date}")
        video_files = filter_videos_by_date(video_files, run_date)
        
        if not video_files:
            print(f"ℹ️  No video files found for date: {run_date}")
            return 0
        
        print(f"📊 Found {len(video_files)} video files matching date {run_date}")
        
        # Apply max files limit if specified (after date filtering)
        if args.max_files:
            video_files = video_files[:args.max_files]
            print(f"📊 Limited to {len(video_files)} files for testing")
        
        # Setup database
        print("🗄️  Setting up database entities...")
        db, org_id, loc_id = setup_database_entities()
        
        # Create run for the date
        run_id = create_run_for_date(db, org_id, loc_id, run_date)
        
        # Setup S3 if needed
        s3 = None
        bucket = None
        if args.download_to_s3:
            from config import Settings
            settings = Settings()
            s3 = get_s3(settings.AWS_REGION)
            bucket = settings.RAW_BUCKET
            print(f"☁️  S3 setup complete, uploading to bucket: {bucket}")
        
        # Process each video file
        imported_count = 0
        for i, file_info in enumerate(video_files, 1):
            print(f"\n📹 Processing file {i}/{len(video_files)}: {file_info['name']}")
            
            # Generate S3 key
            file_basename = os.path.splitext(file_info['name'])[0]
            s3_key = f"{S3_PREFIX}/{file_basename}.mp4"
            
            # Import to database
            video_id = import_video_to_db(db, loc_id, run_id, file_info, s3_key)
            
            # Download to S3 if requested
            if args.download_to_s3:
                success = download_to_s3(gdrive, s3, bucket, file_info, s3_key)
                if not success:
                    print(f"⚠️  Failed to upload {file_info['name']} to S3, but database record created")
            
            imported_count += 1
        
        print(f"\n🎉 Import complete!")
        print(f"📊 Imported {imported_count} video files")
        print(f"🏢 Org ID: {org_id}")
        print(f"📍 Location ID: {loc_id}")
        print(f"🏃 Run ID: {run_id}")
        
        if not args.download_to_s3:
            print("\nℹ️  Videos were not downloaded to S3. To process them:")
            print("   1. Run with --download-to-s3 flag, OR")
            print("   2. Manually upload videos to S3 with the keys shown above")
        
        print(f"\n🔄 To process videos, run: python -m worker.runner")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Import cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
