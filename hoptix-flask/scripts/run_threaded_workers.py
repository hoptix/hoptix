#!/usr/bin/env python3
"""
Threaded video processing script - runs 5 concurrent worker threads
"""

import os
import sys
import time
import threading
import signal
from datetime import datetime
from dotenv import load_dotenv
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from worker.pipeline import fetch_one_uploaded_video, claim_video, process_one_video, mark_status

# Load environment variables
load_dotenv()

# Global shutdown flag
shutdown_flag = threading.Event()
worker_stats = {}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_worker.log'),
        logging.StreamHandler()
    ]
)

def worker_thread(worker_id: int):
    """Individual worker thread function"""
    
    logger = logging.getLogger(f'Worker-{worker_id}')
    
    # Initialize connections for this worker
    try:
        supabase_url = os.environ["SUPABASE_URL"]
        supabase_service_key = os.environ["SUPABASE_SERVICE_KEY"]
        aws_region = os.environ["AWS_REGION"]
        
        db = Supa(supabase_url, supabase_service_key)
        s3 = get_s3(aws_region)
        
        logger.info(f"Worker {worker_id} initialized successfully")
        
    except Exception as e:
        logger.error(f"Worker {worker_id} failed to initialize: {e}")
        return
    
    # Worker stats
    stats = {
        'processed': 0,
        'succeeded': 0,
        'failed': 0,
        'start_time': datetime.now()
    }
    worker_stats[worker_id] = stats
    
    # Main worker loop
    while not shutdown_flag.is_set():
        try:
            # Try to get a video to process
            row = fetch_one_uploaded_video(db)
            if not row:
                # No videos available, wait a bit and try again
                logger.debug(f"No videos available, waiting...")
                time.sleep(2)
                continue
            
            vid = row["id"]
            s3_key = row.get("s3_key", "unknown")
            logger.info(f"Found video to process - ID: {vid}, S3 Key: {s3_key}")
            
            # Try to claim the video (race condition protection)
            if not claim_video(db, vid):
                logger.debug(f"Could not claim video {vid} (another worker got it)")
                continue
            
            logger.info(f"Successfully claimed video {vid}")
            stats['processed'] += 1
            
            # Process the video
            process_start = datetime.now()
            try:
                process_one_video(db, s3, row)
                process_end = datetime.now()
                process_duration = (process_end - process_start).total_seconds()
                
                mark_status(db, vid, "ready")
                stats['succeeded'] += 1
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
                
                stats['failed'] += 1
        
        except Exception as e:
            logger.error(f"Unexpected error in worker {worker_id}: {e}")
            time.sleep(1)  # Brief pause before retrying
    
    # Calculate final stats
    end_time = datetime.now()
    total_time = (end_time - stats['start_time']).total_seconds()
    logger.info(f"Worker {worker_id} shutting down after {total_time:.2f}s. "
               f"Stats: {stats['processed']} processed, {stats['succeeded']} succeeded, {stats['failed']} failed")

def print_stats():
    """Print current worker statistics"""
    print("\n📊 Current Worker Statistics:")
    print("-" * 60)
    total_processed = 0
    total_succeeded = 0
    total_failed = 0
    
    for worker_id, stats in worker_stats.items():
        runtime = (datetime.now() - stats['start_time']).total_seconds()
        rate = stats['processed'] / max(runtime, 1) * 60  # videos per minute
        
        print(f"Worker {worker_id}: {stats['processed']} processed, "
              f"{stats['succeeded']} succeeded, {stats['failed']} failed "
              f"({rate:.1f}/min)")
        
        total_processed += stats['processed']
        total_succeeded += stats['succeeded']
        total_failed += stats['failed']
    
    print("-" * 60)
    print(f"TOTAL: {total_processed} processed, {total_succeeded} succeeded, {total_failed} failed")
    print()

def signal_handler(signum, frame):
    """Handle graceful shutdown"""
    print(f"\n🛑 Received signal {signum}. Initiating graceful shutdown...")
    shutdown_flag.set()

def main():
    """Main function to coordinate multiple worker threads"""
    
    print("🚀 Starting Multi-Threaded Video Processing")
    print("=" * 50)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check environment
    required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "AWS_REGION", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    print("✅ Environment variables loaded")
    
    # Test database connection
    try:
        db = Supa(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        videos = db.client.table("videos").select("id").eq("status", "uploaded").limit(1).execute()
        print(f"✅ Database connection successful")
        
        # Count available videos
        count_result = db.client.table("videos").select("id", count="exact").eq("status", "uploaded").execute()
        video_count = count_result.count if hasattr(count_result, 'count') else len(videos.data)
        print(f"📹 Found {video_count} videos ready for processing")
        
        if video_count == 0:
            print("⚠️ No videos available for processing. Upload some videos first.")
            return
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Start worker threads
    num_workers = 5
    threads = []
    
    print(f"\n🔄 Starting {num_workers} worker threads...")
    
    for i in range(num_workers):
        thread = threading.Thread(target=worker_thread, args=(i + 1,), daemon=True)
        thread.start()
        threads.append(thread)
        print(f"   ✅ Worker thread {i + 1} started")
    
    print(f"\n🎯 All {num_workers} workers are running!")
    print("💡 Press Ctrl+C to stop all workers gracefully")
    print("📊 Stats will be displayed every 30 seconds")
    
    # Monitor threads and display stats
    try:
        last_stats_time = time.time()
        
        while True:
            # Print stats every 30 seconds
            current_time = time.time()
            if current_time - last_stats_time >= 30:
                print_stats()
                last_stats_time = current_time
            
            # Check if all threads are done
            alive_threads = [t for t in threads if t.is_alive()]
            if not alive_threads:
                print("✅ All worker threads have completed")
                break
                
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
        
        # Wait for threads to finish
        print("⏳ Waiting for worker threads to finish...")
        for thread in threads:
            thread.join(timeout=10)
        
        # Final stats
        print_stats()
        print("✅ All workers shut down")

if __name__ == "__main__":
    main()
