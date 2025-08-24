#!/usr/bin/env python3
"""
Multi-worker video processing script - spawns 5 concurrent workers
"""

import os
import sys
import time
import signal
import multiprocessing as mp
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from worker.pipeline import fetch_one_uploaded_video, claim_video, process_one_video, mark_status
from config import Settings

# Load environment variables
load_dotenv()

# Global variables for graceful shutdown
workers = []
shutdown_flag = mp.Event()

def worker_process(worker_id: int, shutdown_event: mp.Event):
    """Individual worker process function"""
    
    # Set up logging for this worker
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s - WORKER-{worker_id} - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'worker_{worker_id}.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(f'worker_{worker_id}')
    
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
    processed = 0
    succeeded = 0
    failed = 0
    
    # Main worker loop
    while not shutdown_event.is_set():
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
            processed += 1
            
            # Process the video
            process_start = datetime.now()
            try:
                process_one_video(db, s3, row)
                process_end = datetime.now()
                process_duration = (process_end - process_start).total_seconds()
                
                mark_status(db, vid, "ready")
                succeeded += 1
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
                
                failed += 1
        
        except KeyboardInterrupt:
            logger.info(f"Worker {worker_id} received interrupt signal")
            break
        except Exception as e:
            logger.error(f"Unexpected error in worker {worker_id}: {e}")
            time.sleep(1)  # Brief pause before retrying
    
    logger.info(f"Worker {worker_id} shutting down. Stats: {processed} processed, {succeeded} succeeded, {failed} failed")

def signal_handler(signum, frame):
    """Handle graceful shutdown"""
    print(f"\n🛑 Received signal {signum}. Initiating graceful shutdown...")
    shutdown_flag.set()
    
    # Wait for workers to finish current tasks
    print("⏳ Waiting for workers to finish current tasks...")
    for worker in workers:
        worker.join(timeout=30)  # Wait up to 30 seconds per worker
        if worker.is_alive():
            print(f"⚠️ Worker {worker.pid} did not shut down gracefully, terminating...")
            worker.terminate()
    
    print("✅ All workers shut down")
    sys.exit(0)

def main():
    """Main function to coordinate multiple workers"""
    
    print("🚀 Starting Multi-Worker Video Processing")
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
    
    # Start workers
    num_workers = 5
    print(f"\n🔄 Starting {num_workers} workers...")
    
    global workers
    for i in range(num_workers):
        worker = mp.Process(target=worker_process, args=(i + 1, shutdown_flag))
        worker.start()
        workers.append(worker)
        print(f"   ✅ Worker {i + 1} started (PID: {worker.pid})")
    
    print(f"\n🎯 All {num_workers} workers are running!")
    print("💡 Press Ctrl+C to stop all workers gracefully")
    print("📊 Monitor individual worker logs: worker_1.log, worker_2.log, etc.")
    
    # Monitor workers
    try:
        while True:
            # Check if any workers have died
            dead_workers = [w for w in workers if not w.is_alive()]
            if dead_workers:
                print(f"⚠️ {len(dead_workers)} workers have stopped")
                
            # Check if all workers are done (no more videos)
            if all(not w.is_alive() for w in workers):
                print("✅ All workers have completed")
                break
                
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    # Set start method for multiprocessing (important for some systems)
    mp.set_start_method('spawn', force=True)
    main()
