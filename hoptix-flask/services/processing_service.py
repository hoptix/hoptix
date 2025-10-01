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

    def process_video_from_local_file_with_clips(self, video_row: Dict, local_video_path: str):
        """Process a video from a local file path including transaction clips and speaker identification"""
        import os
        import tempfile
        import subprocess
        from datetime import datetime
        from dateutil import parser as dateparse
        from worker.clipper import cut_clip_for_transaction, update_tx_meta_with_clip
        # from services.voice_diarization import create_voice_diarization_service
        
        video_id = video_row["id"]
        file_name = video_row.get("meta", {}).get("gdrive_file_name", "Unknown")
        file_size = os.path.getsize(local_video_path) if os.path.exists(local_video_path) else 0
        
        logger.info(f"🎬 Starting full video processing pipeline with clips")
        logger.info(f"   📁 File: {file_name}")
        logger.info(f"   🆔 Video ID: {video_id}")
        logger.info(f"   📏 Size: {file_size:,} bytes")
        logger.info(f"   📍 Local path: {local_video_path}")
        
        start_time = datetime.now()
        
        try:
            # 1) ASR segments
            logger.info(f"🎤 [1/8] Starting audio transcription...")
            segments = transcribe_video(local_video_path)
            logger.info(f"✅ [1/8] Transcription completed: {len(segments)} segments generated")

            # 2) Step‑1 split
            logger.info(f"✂️ [2/8] Starting transaction splitting...")
            txs = split_into_transactions(segments, video_row["started_at"], video_row.get("s3_key"))
            logger.info(f"✅ [2/8] Transaction splitting completed: {len(txs)} transactions identified")

            # 3) Upload artifacts to S3
            logger.info(f"☁️ [3/8] Uploading processing artifacts to S3...")
            prefix = f'deriv/session={video_id}/'
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "segments.jsonl", segments)
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "transactions.jsonl", txs)
            logger.info(f"✅ [3/8] Artifacts uploaded to s3://{self.settings.DERIV_BUCKET}/{prefix}")

            # 4) persist transactions
            logger.info(f"💾 [4/8] Inserting {len(txs)} transactions into database...")
            tx_ids = insert_transactions(self.db, video_row, txs)
            logger.info(f"✅ [4/8] Transactions inserted with IDs: {len(tx_ids)} records")

            # 5) step‑2 grading with location-specific menu data
            location_id = video_row.get("location_id")
            logger.info(f"🎯 [5/8] Starting AI grading for {len(txs)} transactions (location: {location_id})...")
            grades = grade_transactions(txs, self.db, location_id)
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "grades.jsonl", grades)
            logger.info(f"✅ [5/8] Grading completed and uploaded to S3")

            # 6) upsert grades
            logger.info(f"📊 [6/8] Upserting {len(tx_ids)} grades to database...")
            upsert_grades(self.db, tx_ids, grades)
            logger.info(f"✅ [6/8] Grades successfully stored in database")

            # 7) Create and save transaction audio clips with speaker identification
            logger.info(f"🎵 [7/8] Creating transaction audio clips...")
            clip_count = 0
            for i, tx_row in enumerate(txs):
                try:
                    tx_id = tx_ids[i]
                    # Add the transaction ID to the row for the clipper function
                    tx_row_with_id = tx_row.copy()
                    tx_row_with_id['id'] = tx_id
                    
                    audio_file_path = cut_clip_for_transaction(
                        self.db, local_video_path, video_row["started_at"], video_row["ended_at"],
                        tx_row_with_id, video_row["run_id"], video_id
                    )
                    
                    # Process clip for speaker identification
                    # speaker_info = {}
                    # if audio_file_path:
                    #     # For speaker analysis, we'll use the original video segment
                    #     try:
                    #         # Create a temporary clip for speaker analysis
                    #         with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_clip:
                    #             tmp_clip_path = tmp_clip.name
                            
                    #         # Calculate timing offsets for this transaction
                    #         t0 = dateparse.isoparse(tx_row["started_at"])
                    #         t1 = dateparse.isoparse(tx_row["ended_at"])
                    #         video_start = dateparse.isoparse(video_row["started_at"])
                            
                    #         # Calculate seconds from start of video file
                    #         start_offset = (t0 - video_start).total_seconds()
                    #         end_offset = (t1 - video_start).total_seconds()
                            
                    #         # Ensure positive offsets
                    #         start_offset = max(0, start_offset)
                    #         end_offset = max(start_offset + 1.0, end_offset)
                            
                    #         # Use FFmpeg to extract the segment for speaker analysis
                    #         duration = end_offset - start_offset
                    #         cmd = [
                    #             "ffmpeg", "-y",
                    #             "-ss", f"{start_offset:.3f}",
                    #             "-i", local_video_path,
                    #             "-t", f"{duration:.3f}",
                    #             "-c", "copy",
                    #             tmp_clip_path
                    #         ]
                    #         subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            
                    #         # Process for speaker identification
                    #         # if self.settings.ASSEMBLYAI_API_KEY:
                    #         #     logger.info(f"🎤 [8/8] Starting speaker identification for clip {i+1}/{len(txs)}...")
                    #         #     diarization_service = create_voice_diarization_service(
                    #         #         assemblyai_api_key=self.settings.ASSEMBLYAI_API_KEY,
                    #         #         samples_dir=self.settings.SPEAKER_SAMPLES_DIR,
                    #         #         threshold=self.settings.DIARIZATION_THRESHOLD,
                    #         #         min_utterance_ms=self.settings.MIN_UTTERANCE_MS
                    #         #     )
                    #         #     speaker_info = diarization_service.process_clip_for_speakers(tmp_clip_path)
                    #         #     logger.info(f"✅ Speaker identification completed: {speaker_info.get('speakers_detected', [])}")
                    #         # else:
                    #         #     logger.info("ℹ️ AssemblyAI API key not configured - skipping speaker identification")
                            
                    #     except Exception as e:
                    #         logger.warning(f"Failed to analyze clip for speakers: {e}")
                    #     finally:
                    #         if os.path.exists(tmp_clip_path):
                    #             os.remove(tmp_clip_path)
                    
                    # update_tx_meta_with_clip(self.db, tx_id, audio_file_path, speaker_info)
                    # clip_count += 1
                    # logger.info(f"✅ Created audio clip {i+1}/{len(txs)}: {audio_file_path}")
                    
                    # # Print detailed speaker information
                    # if speaker_info and speaker_info.get('speakers_detected'):
                    #     speakers = speaker_info['speakers_detected']
                    #     logger.info(f"   🎤 SPEAKERS IDENTIFIED: {speakers}")
                    #     if isinstance(speakers, list) and len(speakers) > 0:
                    #         for speaker in speakers:
                    #             logger.info(f"      👤 Speaker: {speaker}")
                    # else:
                    #     logger.info(f"   🎤 No speakers identified in this clip")
                except Exception as e:
                    logger.error(f"❌ Failed to create clip for transaction {tx_row.get('id', 'unknown')}: {e}")
            
            logger.info(f"✅ [7/8] Created {clip_count}/{len(txs)} transaction audio clips")
            
            # # 8) Speaker identification summary
            # logger.info(f"🎤 [8/8] Speaker identification completed for {clip_count} clips")
            # if not self.settings.ASSEMBLYAI_API_KEY:
            #     logger.info("   ℹ️ AssemblyAI API key not configured - speaker identification was skipped")
            # else:
            #     logger.info("   ✅ Speaker identification was performed on all clips")
            
            # Final success message
            duration = datetime.now() - start_time
            logger.info(f"🎉 Processing completed successfully!")
            logger.info(f"   ⏱️ Total time: {duration.total_seconds():.1f} seconds")
            logger.info(f"   📈 Results: {len(segments)} segments → {len(txs)} transactions → {len(grades)} grades → {clip_count} clips")
            
        except Exception as e:
            duration = datetime.now() - start_time
            logger.error(f"💥 Processing failed after {duration.total_seconds():.1f} seconds")
            logger.error(f"   🚨 Error: {str(e)}")
            raise

