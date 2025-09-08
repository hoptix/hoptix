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
        """Process a video from a local file path (adapted from process_one_video)"""
        video_id = video_row["id"]
        logger.info(f"Processing video {video_id} from local file: {local_video_path}")
        
        # 1) ASR segments
        logger.info(f"Starting transcription for video {video_id}")
        segments = transcribe_video(local_video_path)
        logger.info(f"Transcription completed: {len(segments)} segments generated")

        # 2) Step‑1 split
        logger.info(f"Starting transaction splitting for video {video_id}")
        txs = split_into_transactions(segments, video_row["started_at"], video_row.get("s3_key"))
        logger.info(f"Transaction splitting completed: {len(txs)} transactions identified")

        # 3) Upload artifacts to S3
        prefix = f'deriv/session={video_id}/'
        logger.info(f"Uploading artifacts to S3 with prefix: {prefix}")
        put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "segments.jsonl", segments)
        put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "transactions.jsonl", txs)
        logger.info("Artifacts uploaded to S3")

        # 4) persist transactions
        logger.info(f"Inserting {len(txs)} transactions into database")
        tx_ids = insert_transactions(self.db, video_row, txs)
        logger.info(f"Inserted transactions with IDs: {tx_ids}")

        # 5) step‑2 grading
        logger.info(f"Starting grading for {len(txs)} transactions")
        grades = grade_transactions(txs)
        put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "grades.jsonl", grades)
        logger.info("Grading completed and uploaded to S3")

        # 6) upsert grades
        logger.info(f"Upserting grades for {len(tx_ids)} transactions")
        upsert_grades(self.db, tx_ids, grades)
        logger.info("Grades upsertion completed")
        
        logger.info(f"Successfully completed all processing steps for video {video_id}")
