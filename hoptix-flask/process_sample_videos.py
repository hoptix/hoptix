#!/usr/bin/env python3
"""
Sample script to process specific DQ Cary videos from Google Drive.
This script will import and process the videos you selected.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, '.')

from config import Settings
from integrations.db_supabase import Supa
from integrations.gdrive_client import GoogleDriveClient
from services.import_service import ImportService
from services.processing_service import ProcessingService
import tempfile

def process_sample_videos():
    """Process the specific DQ Cary videos from Google Drive"""
    
    # Load environment variables
    load_dotenv()
    settings = Settings()
    
    # Initialize services
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    gdrive = GoogleDriveClient()
    
    print("🎬 Processing Sample DQ Cary Videos")
    print("=" * 50)
    
    # List of video files to process (based on what I can see in your Google Drive)
    video_files = [
        "DQ Cary_2025_8_29_13_54_00.mp4",
        "DQ Cary_2025_8_29_13_50_30.mp4", 
        "DQ Cary_2025_8_29_13_46_15.mp4",
        "DQ Cary_2025_8_29_13_43_15.mp4",
        "DQ Cary_2025_8_29_13_38_30.mp4"
    ]
    
    # Create a new run for this batch
    run_id = db.client.table("runs").insert({
        "location_id": "cary-dq-001",  # Adjust this to your actual location ID
        "started_at": datetime.now().isoformat(),
        "status": "processing"
    }).execute()
    
    if not run_id.data:
        print("❌ Failed to create run")
        return
    
    run_id = run_id.data[0]["id"]
    print(f"📋 Created run: {run_id}")
    
    # Process each video
    for i, video_name in enumerate(video_files, 1):
        print(f"\n🎬 Processing video {i}/{len(video_files)}: {video_name}")
        print("-" * 40)
        
        try:
            # Find the video file in Google Drive
            print(f"🔍 Searching for {video_name} in Google Drive...")
            
            # Search for the file by name
            query = f"name='{video_name}' and trashed=false"
            results = gdrive.service.files().list(
                q=query,
                fields="files(id, name, size)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            if not files:
                print(f"❌ Video {video_name} not found in Google Drive")
                continue
                
            file_info = files[0]
            print(f"✅ Found video: {file_info['name']} (ID: {file_info['id']})")
            
            # Create video record in database
            video_id = f"sample-{run_id}-{i:03d}"
            video_data = {
                "id": video_id,
                "run_id": run_id,
                "location_id": "cary-dq-001",  # Adjust to your location ID
                "camera_id": f"gdrive-cam-{file_info['id'][:8]}",
                "s3_key": f"sample/{video_name}",  # Placeholder S3 key
                "started_at": datetime.now().isoformat(),
                "ended_at": datetime.now().isoformat(),
                "status": "uploaded",
                "meta": {
                    "source": "google_drive",
                    "gdrive_file_id": file_info['id'],
                    "gdrive_file_name": file_info['name'],
                    "file_size": file_info.get('size', 0)
                }
            }
            
            # Insert video into database
            db.client.table("videos").upsert(video_data, on_conflict="id").execute()
            print(f"📝 Added video to database: {video_id}")
            
            # Download and process the video
            print(f"⬇️ Downloading video...")
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                tmp_media_path = tmp_file.name
            
            if gdrive.download_file(file_info['id'], tmp_media_path):
                print(f"✅ Downloaded to: {tmp_media_path}")
                
                # Process the video
                print(f"🔧 Starting video processing...")
                processing_service = ProcessingService(db, settings)
                processing_service.process_video_from_local_file_with_clips(video_data, tmp_media_path)
                
                # Mark as ready
                db.client.table("videos").update({"status": "ready"}).eq("id", video_id).execute()
                print(f"✅ Video processing completed!")
                
                # Cleanup
                os.remove(tmp_media_path)
                print(f"🧹 Cleaned up temporary file")
                
            else:
                print(f"❌ Failed to download video")
                db.client.table("videos").update({"status": "failed"}).eq("id", video_id).execute()
                
        except Exception as e:
            print(f"❌ Error processing {video_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Update run status
    db.client.table("runs").update({
        "status": "completed",
        "ended_at": datetime.now().isoformat()
    }).eq("id", run_id).execute()
    
    print(f"\n🎉 Sample video processing completed!")
    print(f"📊 Run ID: {run_id}")
    print(f"📁 Check your Google Drive for the generated clips")

if __name__ == "__main__":
    process_sample_videos()
