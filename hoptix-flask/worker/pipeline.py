import os, time, tempfile, json, datetime as dt, logging, shutil, subprocess
from typing import List, Dict, Tuple
from dateutil import parser as dateparse
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3, download_to_file, put_jsonl
from worker.adapter import transcribe_video, split_into_transactions, grade_transactions
from worker.clipper import cut_clip_for_transaction, update_tx_meta_with_clip
from services.voice_diarization import create_voice_diarization_service

# Configure logging for pipeline
logger = logging.getLogger(__name__)

from config import Settings


def fetch_one_uploaded_video(db: Supa):
    r = db.client.table("videos").select(
        "id, s3_key, run_id, location_id, started_at, ended_at"
    ).eq("status","uploaded").limit(1).execute()
    return r.data[0] if r.data else None


def process_clip_for_speakers(clip_path: str, settings: Settings) -> dict:
    """
    Process a clip for speaker identification using voice diarization.
    
    Args:
        clip_path: Path to the audio/video clip
        settings: Configuration settings
        
    Returns:
        Dictionary with speaker information or empty dict if diarization fails
    """
    try:
        # Only process if AssemblyAI API key is configured
        if not settings.ASSEMBLYAI_API_KEY:
            logger.info("AssemblyAI API key not configured - skipping speaker identification")
            return {}
        
        # Create diarization service
        diarization_service = create_voice_diarization_service(
            assemblyai_api_key=settings.ASSEMBLYAI_API_KEY,
            samples_dir=settings.SPEAKER_SAMPLES_DIR,
            threshold=settings.DIARIZATION_THRESHOLD,
            min_utterance_ms=settings.MIN_UTTERANCE_MS
        )
        
        # Process clip for speakers
        speaker_info = diarization_service.process_clip_for_speakers(clip_path)
        
        logger.info(f"Speaker identification completed: {speaker_info.get('speakers_detected', [])}")
        return speaker_info
        
    except Exception as e:
        logger.error(f"Failed to process clip for speakers: {e}")
        return {}

def process_one_media(db: Supa, s3, media_row: Dict):
    """Process video file (including MKV files)"""
    s3_key = media_row["s3_key"]
    logger.info(f"🎬 Processing video file: {s3_key}")
    return process_one_video(db, s3, media_row)

def claim_video(db: Supa, video_id: str) -> bool:
    r = db.client.table("videos").update({"status":"processing"}) \
        .eq("id", video_id).eq("status","uploaded").execute()
    return bool(r.data)

def mark_status(db: Supa, video_id: str, status: str):
    db.client.table("videos").update({"status":status}).eq("id",video_id).execute()

def insert_transactions(db: Supa, video_row: Dict, transactions: List[Dict]) -> List[str]:
    logger.debug(f"Preparing {len(transactions)} transactions for insertion")
    
    # Handle empty transactions list
    if not transactions:
        logger.warning("No transactions to insert - empty list provided")
        return []
    
    # Log timing information for verification
    for i, tx in enumerate(transactions):
        meta = tx.get("meta", {})
        logger.info(f"Transaction {i+1}: {tx['started_at']} to {tx['ended_at']} "
                   f"(video seconds {meta.get('video_start_seconds', 'N/A')}-{meta.get('video_end_seconds', 'N/A')})")
    
    rows = []
    for tx in transactions:
        rows.append({
            "video_id": video_row["id"],
            "run_id":   video_row["run_id"],
            "started_at": tx["started_at"],
            "ended_at":   tx["ended_at"],
            "tx_range":   f'["{tx["started_at"]}","{tx["ended_at"]}")',
            "kind":       tx.get("kind"),
            "meta":       tx.get("meta", {})
        })
    
    try:
        # Insert transactions - Supabase should return full records by default
        logger.debug(f"Inserting {len(rows)} transaction rows")
        ins = db.client.table("transactions").insert(rows).execute()
        
        if not ins.data:
            logger.error("Failed to insert transactions - no data returned")
            return []
        
        # The insert should return the full records including IDs
        tx_ids = [r["id"] for r in ins.data]
        logger.debug(f"Successfully inserted {len(tx_ids)} transactions")
        return tx_ids
        
    except Exception as e:
        logger.error(f"Error inserting transactions: {str(e)}")
        logger.error(f"Transaction data sample: {rows[0] if rows else 'No rows'}")
        raise



def upsert_grades(db: Supa, tx_ids: List[str], grades: List[Dict]):
    logger.debug(f"Preparing grades for {len(tx_ids)} transactions")
    
    # Handle empty lists
    if not tx_ids or not grades:
        logger.warning("No grades to upsert - empty transaction IDs or grades list")
        return
    
    grads = []
    for tx_id, g in zip(tx_ids, grades):
        d = g.get("details", {}) or {}
        grads.append({
            "transaction_id": tx_id,
            "transcript": g.get("transcript", ""),
            "details": d,
            
            # Basic item counts
            "items_initial": d.get("items_initial"),
            "num_items_initial": d.get("num_items_initial"),
            "items_after": d.get("items_after"),
            "num_items_after": d.get("num_items_after"),
            
            # Upsell fields
            "num_upsell_opportunities": d.get("num_upsell_opportunities"),
            "num_upsell_offers": d.get("num_upsell_offers"),
            "num_upsell_success": d.get("num_upsell_success"),
            "num_largest_offers": d.get("num_largest_offers"),
            "upsell_offered_items": d.get("upsell_offered_items"),
            "upsell_candidate_items": d.get("upsell_candidate_items"),
            "upsell_base_items": d.get("upsell_base_items"),
            "upsell_success_items": d.get("upsell_success_items"),
            
            # Upsize fields
            "num_upsize_opportunities": d.get("num_upsize_opportunities"),
            "num_upsize_offers": d.get("num_upsize_offers"),
            "num_upsize_success": d.get("num_upsize_success"),
            "upsize_offered_items": d.get("upsize_offered_items"),
            "upsize_candidate_items": d.get("upsize_candidate_items"),
            "upsize_base_items": d.get("upsize_base_items"),
            "upsize_success_items": d.get("upsize_success_items"),
            
            # Addon fields
            "num_addon_opportunities": d.get("num_addon_opportunities"),
            "num_addon_offers": d.get("num_addon_offers"),
            "num_addon_success": d.get("num_addon_success"),
            "addon_offered_items": d.get("addon_offered_items"),
            "addon_candidate_items": d.get("addon_candidate_items"),
            "addon_base_items": d.get("addon_base_items"),
            "addon_success_items": d.get("addon_success_items"),
            
            # Meta fields
            "feedback": d.get("feedback"),
            "issues": d.get("issues"),
            "complete_order": d.get("complete_order"),
            "mobile_order": d.get("mobile_order"),
            "coupon_used": d.get("coupon_used"),
            "asked_more_time": d.get("asked_more_time"),
            "out_of_stock_items": d.get("out_of_stock_items"),
            "gpt_price": g.get("gpt_price", 0),
            "reasoning_summary": d.get("reasoning_summary"),
            "video_file_path": d.get("video_file_path"),
            "video_link": d.get("video_link"),
            "score": g.get("score")
        })
    
    if grads:
        try:
            db.client.table("grades").upsert(grads, on_conflict="transaction_id").execute()
            logger.debug(f"Successfully upserted {len(grads)} grades")
        except Exception as e:
            logger.error(f"Error upserting grades: {str(e)}")
            raise
    else:
        logger.warning("No grades to upsert")

def process_one_video(db: Supa, s3, video_row: Dict):
    """Process a single video with enhanced logging and progress tracking"""
    from datetime import datetime
    
    video_id = video_row["id"]
    s3_key = video_row["s3_key"]
    
    logger.info(f"🎬 Starting video processing pipeline")
    logger.info(f"   🆔 Video ID: {video_id}")
    logger.info(f"   🗂️ S3 Key: {s3_key}")
    
    settings = Settings()
    tmpdir = tempfile.mkdtemp(prefix="hoptix_")
    local_path = os.path.join(tmpdir, "input.mp4")
    start_time = datetime.now()
    
    try:
        # Download video
        logger.info(f"📥 [1/6] Downloading video from S3...")
        download_to_file(s3, settings.RAW_BUCKET, s3_key, local_path)
        
        # Get file size for logging
        file_size = os.path.getsize(local_path)
        logger.info(f"✅ [1/6] Video downloaded ({file_size:,} bytes) to: {local_path}")

        # 1) ASR segments
        logger.info(f"🎤 [2/6] Starting audio transcription...")
        segments = transcribe_video(local_path)
        logger.info(f"✅ [2/6] Transcription completed: {len(segments)} segments generated")

        # 2) Step‑1 split
        logger.info(f"✂️ [3/6] Starting transaction splitting...")
        txs = split_into_transactions(segments, video_row["started_at"], s3_key)
        logger.info(f"✅ [3/6] Transaction splitting completed: {len(txs)} transactions identified")

        # artifacts
        logger.info(f"☁️ [4/6] Uploading processing artifacts to S3...")
        prefix = f'deriv/session={video_id}/'
        put_jsonl(s3, settings.DERIV_BUCKET, prefix + "segments.jsonl", segments)
        put_jsonl(s3, settings.DERIV_BUCKET, prefix + "transactions.jsonl", txs)
        logger.info(f"✅ [4/6] Artifacts uploaded to s3://{settings.DERIV_BUCKET}/{prefix}")

        # 3) persist transactions
        logger.info(f"💾 [5/6] Inserting {len(txs)} transactions into database...")
        tx_ids = insert_transactions(db, video_row, txs)
        logger.info(f"✅ [5/6] Transactions inserted: {len(tx_ids)} records")

        # 4) step‑2 grading with location-specific menu data
        location_id = video_row.get("location_id")
        logger.info(f"🎯 [6/6] Starting AI grading for {len(txs)} transactions (location: {location_id})...")
        grades = grade_transactions(txs, db, location_id)
        put_jsonl(s3, settings.DERIV_BUCKET, prefix + "grades.jsonl", grades)
        logger.info(f"✅ [6/6] Grading completed and uploaded to S3")

        # 5) upsert grades
        logger.info(f"📊 Upserting {len(tx_ids)} grades to database...")
        upsert_grades(db, tx_ids, grades)
        logger.info(f"✅ Grades successfully stored in database")

        # 6) Create and upload transaction clips with speaker identification
        logger.info(f"🎬 [7/8] Creating transaction clips...")
        clip_count = 0
        for i, tx_row in enumerate(txs):
            try:
                tx_id = tx_ids[i]
                # Add the transaction ID to the row for the clipper function
                tx_row_with_id = tx_row.copy()
                tx_row_with_id['id'] = tx_id
                
                gdrive_file_id = cut_clip_for_transaction(
                    db, local_path, video_row["started_at"], video_row["ended_at"],
                    tx_row_with_id, video_row["run_id"], video_id
                )
                
                # Process clip for speaker identification
                speaker_info = {}
                if gdrive_file_id:
                    # For speaker analysis, we'll use the original video segment
                    # since we don't want to download from Google Drive just for analysis
                    try:
                        # Create a temporary clip for speaker analysis
                        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_clip:
                            tmp_clip_path = tmp_clip.name
                        
                        # Calculate timing offsets for this transaction
                        t0 = dateparse.isoparse(tx_row["started_at"])
                        t1 = dateparse.isoparse(tx_row["ended_at"])
                        video_start = dateparse.isoparse(video_row["started_at"])
                        
                        # Calculate seconds from start of video file
                        start_offset = (t0 - video_start).total_seconds()
                        end_offset = (t1 - video_start).total_seconds()
                        
                        # Ensure positive offsets
                        start_offset = max(0, start_offset)
                        end_offset = max(start_offset + 1.0, end_offset)
                        
                        # Use FFmpeg to extract the segment for speaker analysis
                        duration = end_offset - start_offset
                        cmd = [
                            "ffmpeg", "-y",
                            "-ss", f"{start_offset:.3f}",
                            "-i", local_path,
                            "-t", f"{duration:.3f}",
                            "-c", "copy",
                            tmp_clip_path
                        ]
                        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        speaker_info = process_clip_for_speakers(tmp_clip_path, settings)
                        
                    except Exception as e:
                        logger.warning(f"Failed to analyze clip for speakers: {e}")
                    finally:
                        if os.path.exists(tmp_clip_path):
                            os.remove(tmp_clip_path)
                
                update_tx_meta_with_clip(db, tx_id, gdrive_file_id, speaker_info)
                clip_count += 1
                logger.info(f"✅ Created clip {i+1}/{len(txs)}: Google Drive ID {gdrive_file_id}")
                if speaker_info.get('speakers_detected'):
                    logger.info(f"   🎤 Speakers detected: {speaker_info['speakers_detected']}")
            except Exception as e:
                logger.error(f"❌ Failed to create clip for transaction {tx_row.get('id', 'unknown')}: {e}")
        
        logger.info(f"✅ [7/8] Created {clip_count}/{len(txs)} transaction clips")
        
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
        
    finally:
        # Cleanup temporary files
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                if os.path.exists(tmpdir):
                    shutil.rmtree(tmpdir, ignore_errors=True)
            logger.info(f"Cleaned up temporary files for video {video_id}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup temporary files: {cleanup_error}")

def main_loop():
    s = Settings()
    db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)
    s3 = get_s3(s.AWS_REGION)

    while True:
        row = fetch_one_uploaded_video(db)
        if not row:
            time.sleep(3); continue
        media_id = row["id"]
        if not claim_video(db, media_id):
            continue
        try:
            process_one_media(db, s3, row)
            mark_status(db, media_id, "ready")
        except Exception as e:
            print("worker error:", e)
            mark_status(db, media_id, "failed")
            time.sleep(2)