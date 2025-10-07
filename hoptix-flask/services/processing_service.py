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

            # 7) Create and save transaction audio clips (speaker identification disabled)
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
                    
                    # Process clip for speaker identification (DISABLED)
                    speaker_info = {}  # Empty speaker info since diarization is disabled
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
                    
                    update_tx_meta_with_clip(
                        self.db,
                        tx_id,
                        audio_file_path,
                        speaker_info,
                        run_id=video_row.get("run_id"),
                        tx_started_at=tx_row_with_id.get("started_at"),
                        tx_ended_at=tx_row_with_id.get("ended_at")
                    )
                    clip_count += 1
                    logger.info(f"✅ Created audio clip {i+1}/{len(txs)}: {audio_file_path}")
                    
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


    def process_wav_from_local_file(self, video_row: Dict, local_wav_path: str):
        """Process a WAV audio file directly (no video extraction required).

        The provided "video_row" should be a row shaped like entries in the
        videos table (id/run_id/location_id/started_at/etc.). This method will:
          1) Segment and transcribe the WAV using the ASR model
          2) Split into transactions
          3) Upload artifacts to S3
          4) Insert transactions and grade them
          5) Upsert grades
        """
        import os
        from datetime import datetime
        import librosa
        import numpy as np
        import soundfile as sf
        from openai import OpenAI
        from worker.adapter import _segment_active_spans

        video_id = video_row["id"]
        file_name = video_row.get("meta", {}).get("gdrive_file_name", os.path.basename(local_wav_path))
        file_size = os.path.getsize(local_wav_path) if os.path.exists(local_wav_path) else 0

        logger.info(f"🎵 Starting WAV processing pipeline")
        logger.info(f"   📁 File: {file_name}")
        logger.info(f"   🆔 Video ID: {video_id}")
        logger.info(f"   📏 Size: {file_size:,} bytes")
        logger.info(f"   📍 Local path: {local_wav_path}")

        start_time = datetime.now()

        try:
            # 1) Get WAV file info without loading entire file into memory
            logger.info(f"🎤 [1/6] Analyzing WAV file structure...")
            
            # Get file info using soundfile (more memory efficient)
            with sf.SoundFile(local_wav_path) as f:
                sr = f.samplerate
                frames = f.frames
                duration_s = frames / float(sr)
                channels = f.channels
                
            logger.info(f"📊 WAV Info: {duration_s:.1f}s, {sr}Hz, {channels} channels, {frames:,} frames")
            
            # For large files, use a simpler segmentation approach to avoid memory issues
            # Since we're already working with chunks from the splitter, we can process more directly
            max_seg_s = 1200.0  # 20 minutes max per segment
            
            # Create segments based on duration rather than loading entire file
            if duration_s <= max_seg_s:
                # File is small enough to process as one segment
                final_spans = [(0.0, duration_s)]
                logger.info(f"📏 File is small enough ({duration_s:.1f}s), processing as single segment")
            else:
                # Split into 20-minute chunks with small overlap
                overlap_s = 5.0  # 5 second overlap
                final_spans = []
                current_start = 0.0
                
                while current_start < duration_s:
                    current_end = min(current_start + max_seg_s, duration_s)
                    final_spans.append((current_start, current_end))
                    current_start = current_end - overlap_s
                    
                logger.info(f"📏 File split into {len(final_spans)} segments of ~{max_seg_s/60:.1f}min each")

            # 2) Transcribe each segment using memory-efficient approach
            logger.info(f"🧩 Processing {len(final_spans)} audio segments for ASR")
            client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            audio_dir = "extracted_audio"
            os.makedirs(audio_dir, exist_ok=True)
            base = os.path.splitext(file_name)[0]

            segments = []
            for i, (b, e) in enumerate(final_spans, start=1):
                logger.info(f"🎵 Processing segment {i}/{len(final_spans)}: {b:.1f}s - {e:.1f}s")
                
                # Extract segment using soundfile (memory efficient)
                seg_path = os.path.join(audio_dir, f"{base}_seg_{i:03d}_{int(b)}s-{int(e)}s.wav")
                
                try:
                    # Use soundfile to extract just this segment
                    with sf.SoundFile(local_wav_path) as f:
                        # Seek to start position
                        f.seek(int(b * sr))
                        # Read only the frames we need
                        frames_to_read = int((e - b) * sr)
                        seg_data = f.read(frames_to_read)
                        
                    # Write segment to file
                    sf.write(seg_path, seg_data, sr)
                    
                    # Transcribe the segment
                    with open(seg_path, "rb") as af:
                        txt = client.audio.transcriptions.create(
                            model=self.settings.ASR_MODEL,
                            file=af,
                            response_format="text",
                            temperature=0.001,
                            prompt="Label each line as Operator: or Customer: where possible."
                        )
                    text = str(txt)
                    logger.info(f"✅ ASR {i}/{len(final_spans)}: {len(text)} chars")
                    
                    # Clean up segment file immediately to save disk space
                    os.remove(seg_path)
                    
                except Exception as asr_err:
                    logger.warning(f"❌ ASR failed for segment {i}: {asr_err}")
                    text = ""
                    # Clean up failed segment file
                    if os.path.exists(seg_path):
                        os.remove(seg_path)
                        
                segments.append({"start": float(b), "end": float(e), "text": text})

            logger.info(f"✅ [1/6] Transcription completed: {len(segments)} segments generated")

            # 3) Split into transactions
            logger.info(f"✂️ [2/6] Starting transaction splitting...")
            txs = split_into_transactions(segments, video_row["started_at"], video_row.get("s3_key"))
            logger.info(f"✅ [2/6] Transaction splitting completed: {len(txs)} transactions identified")

            # 4) Upload artifacts to S3
            logger.info(f"☁️ [3/6] Uploading processing artifacts to S3...")
            prefix = f'deriv/session={video_id}/'
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "segments.jsonl", segments)
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "transactions.jsonl", txs)
            logger.info(f"✅ [3/6] Artifacts uploaded to s3://{self.settings.DERIV_BUCKET}/{prefix}")

            # 5) persist transactions
            logger.info(f"💾 [4/6] Inserting {len(txs)} transactions into database...")
            tx_ids = insert_transactions(self.db, video_row, txs)
            logger.info(f"✅ [4/6] Transactions inserted with IDs: {len(tx_ids)} records")

            # 6) grading
            location_id = video_row.get("location_id")
            logger.info(f"🎯 [5/6] Starting AI grading for {len(txs)} transactions (location: {location_id})...")
            grades = grade_transactions(txs, self.db, location_id)
            put_jsonl(self.s3, self.settings.DERIV_BUCKET, prefix + "grades.jsonl", grades)
            logger.info(f"✅ [5/6] Grading completed and uploaded to S3")

            # 7) upsert grades
            logger.info(f"📊 [6/6] Upserting {len(tx_ids)} grades to database...")
            upsert_grades(self.db, tx_ids, grades)
            logger.info(f"✅ [6/6] Grades successfully stored in database")

            # Final success
            duration = datetime.now() - start_time
            logger.info(f"🎉 WAV Processing completed successfully!")
            logger.info(f"   ⏱️ Total time: {duration.total_seconds():.1f} seconds")
            logger.info(f"   📈 Results: {len(segments)} segments → {len(txs)} transactions → {len(grades)} grades")

        except Exception as e:
            duration = datetime.now() - start_time
            logger.error(f"💥 WAV Processing failed after {duration.total_seconds():.1f} seconds")
            logger.error(f"   🚨 Error: {str(e)}")
            raise

