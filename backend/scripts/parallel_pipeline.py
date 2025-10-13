#!/usr/bin/env python3
"""
Backend Parallel Media Processing Pipeline
Based on the working AVI pipeline script that successfully processed 11 parallel 1.2GB files
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import DatabaseService
from services.import_service import ImportService
from services.audio_processor import transcribe_audio_file
from config import Settings

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def import_files(org_id: str, location_id: str, date: str) -> str:
    """Step 1: Import media files from Google Drive"""
    print("📥 Step 1: Importing media files from Google Drive...")
    
    try:
        settings = Settings()
        db = DatabaseService(settings)
        
        # Get folder name from location
        folder_name = db.get_location_name(location_id)
        print(f'📁 Using folder name: {folder_name}')
        
        # Initialize import service
        import_service = ImportService(db, settings, folder_name)
        
        # Import videos from Google Drive
        imported_video_ids = import_service.import_videos_from_gdrive(org_id, location_id, date)
        
        print(f'✅ Successfully imported {len(imported_video_ids)} videos')
        if imported_video_ids:
            print('📋 Imported video IDs:', ', '.join(imported_video_ids))
        
        # Get the run_id from one of the imported videos
        if imported_video_ids:
            run_id = db.get_run_id_from_video(imported_video_ids[0])
            print(f'🆔 Found run_id: {run_id}')
            return run_id
        else:
            print('❌ No videos imported')
            sys.exit(1)
            
    except Exception as e:
        print(f'❌ Import failed: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

def get_media_files(run_id: str) -> List[str]:
    """Step 2: Get list of media files to process"""
    print("📋 Step 2: Getting list of media files to process...")
    
    try:
        settings = Settings()
        db = DatabaseService(settings)
        
        print(f'🔍 Looking for videos with run_id: {run_id}')
        
        # Get all media files for this run_id first to see their status
        all_videos = db.get_videos_by_run_id(run_id)
        print(f'📊 Found {len(all_videos)} total videos in database:')
        for video in all_videos:
            print(f'  - ID: {video["id"]}, Status: {video["status"]}')
        
        # Get uploaded media files for this run_id
        uploaded_videos = db.get_uploaded_videos_by_run_id(run_id)
        print(f'✅ Found {len(uploaded_videos)} uploaded videos')
        
        media_ids = [video['id'] for video in uploaded_videos]
        return media_ids
        
    except Exception as e:
        print(f'❌ Failed to get media files: {e}')
        sys.exit(1)

def process_media_worker(media_id: str, worker_id: int) -> Dict:
    """Process a single media file (worker function)"""
    try:
        settings = Settings()
        db = DatabaseService(settings)
        
        start_time = datetime.now()
        print(f'🚀 [Worker {worker_id}] Starting processing at {start_time.strftime("%H:%M:%S")}')
        print(f'📋 [Worker {worker_id}] Processing media: {media_id}')
        
        # Claim media file
        print(f'🔒 [Worker {worker_id}] Attempting to claim media {media_id}...')
        if not db.claim_video(media_id):
            print(f'❌ [Worker {worker_id}] Could not claim media {media_id} - may be already claimed')
            return {"status": "failed", "reason": "could_not_claim"}
        
        print(f'✅ [Worker {worker_id}] Successfully claimed media {media_id}')
        
        # Get media details
        print(f'📋 [Worker {worker_id}] Fetching media details from database...')
        media_row = db.get_video_by_id(media_id)
        if not media_row:
            print(f'❌ [Worker {worker_id}] Media {media_id} not found in database')
            return {"status": "failed", "reason": "not_found"}
        
        # Download and process the file
        # This is where you'd implement the download and processing logic
        # For now, we'll use the audio processor directly
        
        print(f'🎵 [Worker {worker_id}] Starting audio processing...')
        processing_start = datetime.now()
        
        # Use the hoptix-flask approach
        segments = transcribe_audio_file(media_row['local_path'])
        
        processing_time = (datetime.now() - processing_start).total_seconds()
        print(f'✅ [Worker {worker_id}] Processing completed in {processing_time:.1f}s')
        
        # Mark as ready
        db.mark_video_status(media_id, 'ready')
        
        total_time = (datetime.now() - start_time).total_seconds()
        print(f'🎉 [Worker {worker_id}] Successfully processed media {media_id} in {total_time:.1f}s total')
        
        return {"status": "success", "segments": len(segments), "time": total_time}
        
    except Exception as e:
        print(f'❌ [Worker {worker_id}] Fatal error processing media {media_id}: {e}')
        import traceback
        traceback.print_exc()
        try:
            db.mark_video_status(media_id, 'failed')
        except:
            pass
        return {"status": "failed", "reason": str(e)}

def process_parallel(media_files: List[str], num_workers: int):
    """Step 3: Process media files in parallel"""
    print(f"📊 Found {len(media_files)} media files to process")
    print(f"🚀 Starting {num_workers} parallel workers...")
    print("")
    
    results = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        future_to_media = {
            executor.submit(process_media_worker, media_id, i+1): media_id
            for i, media_id in enumerate(media_files)
        }
        
        # Collect results as they complete
        completed_count = 0
        for future in as_completed(future_to_media):
            media_id = future_to_media[future]
            completed_count += 1
            
            try:
                result = future.result()
                results.append(result)
                print(f"✅ Worker {completed_count}/{len(media_files)} completed: {media_id}")
            except Exception as e:
                print(f"❌ Worker {completed_count}/{len(media_files)} failed: {media_id} - {e}")
                results.append({"status": "failed", "reason": str(e)})
    
    # Print summary
    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful
    
    print("")
    print("📊 Processing Summary:")
    print("==============================")
    print(f"✅ Successfully processed: {successful}")
    print(f"❌ Failed: {failed}")
    
    return results

def run_analytics(run_id: str):
    """Step 4: Run analytics on processed transactions"""
    print("📊 Step 4: Running analytics on processed transactions...")
    
    try:
        settings = Settings()
        db = DatabaseService(settings)
        
        # Get graded transactions for this run
        transactions = db.get_graded_transactions_by_run_id(run_id)
        
        if not transactions:
            print('ℹ️ No graded transactions found for this run')
            return
        
        print(f'📋 Found {len(transactions)} graded transactions for analysis')
        
        # Here you would run your analytics logic
        # For now, just print a summary
        print('📊 Analytics completed (placeholder)')
        
    except Exception as e:
        print(f'❌ Analytics failed: {e}')

def main():
    parser = argparse.ArgumentParser(description='Backend Parallel Media Processing Pipeline')
    parser.add_argument('org_id', help='Organization ID')
    parser.add_argument('location_id', help='Location ID')
    parser.add_argument('date', nargs='?', help='Processing date (YYYY-MM-DD)')
    parser.add_argument('num_workers', nargs='?', type=int, default=11, help='Number of workers')
    
    args = parser.parse_args()
    
    setup_logging()
    
    print("🚀 Backend Parallel Media Processing Pipeline")
    print("=============================================")
    print(f"🏢 Organization ID: {args.org_id}")
    print(f"📍 Location ID: {args.location_id}")
    print(f"📅 Processing date: {args.date}")
    print(f"👥 Number of workers: {args.num_workers}")
    print("")
    
    try:
        # Step 1: Import files
        run_id = import_files(args.org_id, args.location_id, args.date)
        print(f"🔄 Run ID: {run_id}")
        print("")
        
        # Step 2: Get media files
        media_files = get_media_files(run_id)
        if not media_files:
            print("ℹ️ No media files found to process")
            return
        print("")
        
        # Step 3: Process in parallel
        results = process_parallel(media_files, args.num_workers)
        print("")
        
        # Step 4: Run analytics
        run_analytics(run_id)
        print("")
        
        print("✅ Parallel pipeline completed!")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
