#!/usr/bin/env python3
"""
SQS-based video processing worker - replaces polling-based approach
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Settings
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from integrations.sqs_client import get_sqs_client
from worker.pipeline import process_one_video, mark_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SQSVideoWorker:
    """SQS-based worker for processing video messages"""
    
    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        self.shutdown = False
        self.current_message = None
        self.current_receipt_handle = None
        
        # Initialize settings and connections
        self.settings = Settings()
        self._validate_settings()
        
        self.db = Supa(self.settings.SUPABASE_URL, self.settings.SUPABASE_SERVICE_KEY)
        self.s3 = get_s3(self.settings.AWS_REGION)
        self.sqs = get_sqs_client(
            self.settings.AWS_REGION,
            self.settings.SQS_QUEUE_URL,
            self.settings.SQS_DLQ_URL
        )
        
        # Stats tracking
        self.stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "started_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "last_activity": datetime.now()
        }
        
        logger.info(f"SQS Worker {self.worker_id} initialized")
        logger.info(f"Queue URL: {self.settings.SQS_QUEUE_URL}")
        
    def _validate_settings(self):
        """Validate required settings"""
        if not self.settings.SQS_QUEUE_URL:
            raise ValueError("SQS_QUEUE_URL is required")
        if not self.settings.SUPABASE_URL:
            raise ValueError("SUPABASE_URL is required")
        if not self.settings.SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_SERVICE_KEY is required")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Worker {self.worker_id} received signal {signum}, shutting down gracefully...")
            self.shutdown = True
            
            # If we're currently processing a message, extend its visibility
            if self.current_receipt_handle:
                logger.info("Extending message visibility for graceful shutdown...")
                self.sqs.change_message_visibility(self.current_receipt_handle, 60)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _extend_message_visibility(self, receipt_handle: str, additional_seconds: int = 600):
        """Extend message visibility for long-running processing"""
        try:
            current_timeout = self.settings.SQS_VISIBILITY_TIMEOUT + additional_seconds
            max_timeout = 12 * 60 * 60  # SQS max is 12 hours
            
            new_timeout = min(current_timeout, max_timeout)
            self.sqs.change_message_visibility(receipt_handle, new_timeout)
            logger.debug(f"Extended message visibility to {new_timeout} seconds")
            
        except Exception as e:
            logger.warning(f"Failed to extend message visibility: {e}")
    
    def _log_heartbeat(self):
        """Log periodic heartbeat to show worker is alive"""
        now = datetime.now()
        runtime = now - self.stats["started_at"]
        last_activity_ago = now - self.stats["last_activity"]
        
        logger.info(f"💓 Worker {self.worker_id} HEARTBEAT - Runtime: {runtime}, "
                   f"Processed: {self.stats['processed']}, "
                   f"Success Rate: {self._get_success_rate():.1f}%, "
                   f"Last Activity: {last_activity_ago} ago")
        
        self.stats["last_heartbeat"] = now
    
    def _get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.stats["processed"] == 0:
            return 100.0
        return (self.stats["succeeded"] / self.stats["processed"]) * 100
    
    def _mark_video_processing(self, video_id: str) -> bool:
        """Mark video as processing in database"""
        try:
            result = self.db.client.table("videos").update({"status": "processing"}) \
                .eq("id", video_id).eq("status", "uploaded").execute()
            
            if not result.data:
                logger.warning(f"Could not claim video {video_id} (may already be processing)")
                return False
            
            logger.info(f"Successfully claimed video {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark video {video_id} as processing: {e}")
            return False
    
    def process_message(self, message_data: Dict) -> bool:
        """
        Process a single video message
        
        Args:
            message_data: Dictionary containing video data and SQS metadata
            
        Returns:
            True if successful, False if failed
        """
        video_data = message_data['video_data']
        receipt_handle = message_data['receipt_handle']
        
        self.current_receipt_handle = receipt_handle
        video_id = video_data['video_id']
        
        try:
            logger.info(f"Worker {self.worker_id} processing video {video_id}")
            
            # Mark video as processing (idempotent check)
            if not self._mark_video_processing(video_id):
                # Video may already be processed or processing
                logger.info(f"Video {video_id} already claimed or processed, skipping")
                return True
            
            # Prepare video data for pipeline
            video_row = {
                "id": video_data["video_id"],
                "s3_key": video_data["s3_key"],
                "run_id": video_data["run_id"],
                "location_id": video_data["location_id"],
                "started_at": video_data["started_at"],
                "ended_at": video_data["ended_at"]
            }
            
            # Extend visibility for long processing
            self._extend_message_visibility(receipt_handle)
            
            # Process the video through the pipeline
            start_time = time.time()
            process_one_video(self.db, self.s3, video_row)
            duration = time.time() - start_time
            
            # Mark as ready
            mark_status(self.db, video_id, "ready")
            
            # Update stats
            self.stats["processed"] += 1
            self.stats["succeeded"] += 1
            self.stats["last_activity"] = datetime.now()
            
            logger.info(f"✅ Worker {self.worker_id} completed video {video_id} in {duration:.2f}s")
            return True
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"❌ Worker {self.worker_id} failed video {video_id} after {duration:.2f}s: {e}")
            
            # Mark as failed
            try:
                mark_status(self.db, video_id, "failed")
            except Exception as mark_error:
                logger.error(f"Failed to mark video {video_id} as failed: {mark_error}")
            
            # Update stats
            self.stats["processed"] += 1
            self.stats["failed"] += 1
            
            return False
            
        finally:
            self.current_receipt_handle = None
    
    def run(self):
        """Main worker loop"""
        logger.info(f"🚀 SQS Worker {self.worker_id} starting...")
        logger.info(f"🔧 Worker PID: {os.getpid()}")
        logger.info(f"⏰ Started at: {self.stats['started_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🌐 Region: {self.settings.AWS_REGION}")
        self._setup_signal_handlers()
        
        # Print queue stats on startup
        queue_stats = self.sqs.get_queue_attributes()
        logger.info(f"📊 Queue stats at startup: {queue_stats}")
        logger.info(f"✅ Worker {self.worker_id} is ACTIVE and waiting for messages...")
        
        # Heartbeat counter for periodic status logging
        heartbeat_counter = 0
        heartbeat_interval = 60  # Log heartbeat every 60 iterations (roughly every 20 minutes with 20s polling)
        
        while not self.shutdown:
            try:
                # Receive message from SQS (long polling)
                message_data = self.sqs.receive_video_message(
                    wait_time_seconds=self.settings.SQS_WAIT_TIME,
                    visibility_timeout=self.settings.SQS_VISIBILITY_TIMEOUT
                )
                
                if not message_data:
                    # No messages available, continue polling
                    logger.debug(f"🔍 Worker {self.worker_id} - no messages available, continuing to poll...")
                    
                    # Periodic heartbeat logging
                    heartbeat_counter += 1
                    if heartbeat_counter >= heartbeat_interval:
                        self._log_heartbeat()
                        heartbeat_counter = 0
                    
                    continue
                
                # Process the message
                success = self.process_message(message_data)
                
                if success:
                    # Delete message from queue
                    self.sqs.delete_message(message_data['receipt_handle'])
                    logger.debug(f"Deleted message {message_data['message_id']} from queue")
                else:
                    # Message will return to queue after visibility timeout
                    # SQS will handle retries and eventual move to DLQ
                    logger.warning(f"Message {message_data['message_id']} will be retried")
                
                # Brief pause between messages to avoid overwhelming
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info(f"Worker {self.worker_id} interrupted by user")
                break
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error in main loop: {e}")
                time.sleep(5)  # Brief pause before retrying
        
        self._shutdown_gracefully()
    
    def _shutdown_gracefully(self):
        """Graceful shutdown"""
        runtime = datetime.now() - self.stats["started_at"]
        
        logger.info(f"🛑 Worker {self.worker_id} shutting down")
        logger.info(f"📊 Final stats: {self.stats['processed']} processed, "
                   f"{self.stats['succeeded']} succeeded, {self.stats['failed']} failed")
        logger.info(f"⏱️ Runtime: {runtime}")
        
        # Log final queue stats
        try:
            queue_stats = self.sqs.get_queue_attributes()
            dlq_stats = self.sqs.get_dlq_attributes()
            logger.info(f"📋 Final queue stats: {queue_stats}")
            if dlq_stats:
                logger.info(f"💀 DLQ stats: {dlq_stats}")
        except Exception as e:
            logger.warning(f"Failed to get final queue stats: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SQS Video Processing Worker')
    parser.add_argument('--worker-id', help='Unique worker identifier')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        worker = SQSVideoWorker(worker_id=args.worker_id)
        worker.run()
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
