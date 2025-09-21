import logging
from typing import Dict
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3, put_jsonl
from worker.adapter import transcribe_video, split_into_transactions, grade_transactions
from worker.pipeline import insert_transactions, upsert_grades
from config import Settings

logger = logging.getLogger(__name__)

class ProcessingService:
    """Video processing coordination service."""
    
    def __init__(self, db: Supa, settings: Settings):
        self.db = db
        self.settings = settings
        self.s3 = get_s3(settings.AWS_REGION)
    
    def process_video_from_local_file(self, video_row: Dict, local_video_path: str):
        """Process a video from a local file path with enhanced logging"""
        import os
        from datetime import datetime
        
        video_id = video_row["id"]
        file_name = video_row.get("meta", {}).get("gdrive_file_name", "Unknown")
        file_size = os.path.getsize(local_video_path) if os.path.exists(local_video_path) else 0
        
        logger.info(f"🎬 Starting video processing pipeline")
        logger.info(f"   📁 File: {file_name}")
        logger.info(f"   🆔 Video ID: {video_id}")
        logger.info(f"   📏 Size: {file_size:,} bytes")
        logger.info(f"   📍 Local path: {local_video_path}")
        
        start_time = datetime.now()
        
        try:
            # 1) ASR segments
            logger.info(f"🎤 [1/6] Starting audio transcription...")
            segments = transcribe_video(local_video_path)
            logger.info(f"✅ [1/6] Transcription completed: {len(segments)} segments generated")

            # 2) Step‑1 split
            logger.info(f"✂️ [2/6] Starting transaction splitting...")
            txs = split_into_transactions(segments, video_row["started_at"], video_row.get("s3_key"))
            logger.info(f"✅ [2/6] Transaction splitting completed: {len(txs)} transactions identified")

            # 3) Upload artifacts to S3
            logger.info(f"☁️ [3/6] Uploading processing artifacts to S3...")
            prefix = f'deriv/session={video_id}/'
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "segments.jsonl", segments)
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "transactions.jsonl", txs)
            logger.info(f"✅ [3/6] Artifacts uploaded to s3://{self.settings.DERIV_BUCKET}/{prefix}")

            # 4) persist transactions
            logger.info(f"💾 [4/6] Inserting {len(txs)} transactions into database...")
            tx_ids = insert_transactions(self.db, video_row, txs)
            logger.info(f"✅ [4/6] Transactions inserted with IDs: {len(tx_ids)} records")

            # 5) step‑2 grading with location-specific menu data
            location_id = video_row.get("location_id")
            logger.info(f"🎯 [5/6] Starting AI grading for {len(txs)} transactions (location: {location_id})...")
            grades = grade_transactions(txs, self.db, location_id)
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "grades.jsonl", grades)
            logger.info(f"✅ [5/6] Grading completed and uploaded to S3")

            # 6) upsert grades
            logger.info(f"📊 [6/6] Upserting {len(tx_ids)} grades to database...")
            upsert_grades(self.db, tx_ids, grades)
            logger.info(f"✅ [6/6] Grades successfully stored in database")
            
            # Final success message
            duration = datetime.now() - start_time
            logger.info(f"🎉 Processing completed successfully!")
            logger.info(f"   ⏱️ Total time: {duration.total_seconds():.1f} seconds")
            logger.info(f"   📈 Results: {len(segments)} segments → {len(txs)} transactions → {len(grades)} grades")
            
        except Exception as e:
            duration = datetime.now() - start_time
            logger.error(f"💥 Processing failed after {duration.total_seconds():.1f} seconds")
            logger.error(f"   🚨 Error: {str(e)}")
            raise
