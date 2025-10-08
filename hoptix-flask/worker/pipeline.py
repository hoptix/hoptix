import os, time, tempfile, json, datetime as dt, logging, shutil, subprocess
from typing import List, Dict, Tuple
from dateutil import parser as dateparse
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3, download_to_file, put_jsonl
from worker.adapter import transcribe_video, split_into_transactions, grade_transactions
from worker.clipper import cut_clip_for_transaction, update_tx_meta_with_clip
# from services.voice_diarization import create_voice_diarization_service

# Configure logging for pipeline
logger = logging.getLogger(__name__)

from config import Settings


def fetch_one_uploaded_video(db: Supa):
    r = db.client.table("videos").select(
        "id, s3_key, run_id, location_id, started_at, ended_at"
    ).eq("status","uploaded").limit(1).execute()
    return r.data[0] if r.data else None


# def process_clip_for_speakers(clip_path: str, settings: Settings) -> dict:
#     """
#     Process a clip for speaker identification using voice diarization.
#     
#     Args:
#         clip_path: Path to the audio/video clip
#         settings: Configuration settings
#         
#     Returns:
#         Dictionary with speaker information or empty dict if diarization fails
#     """
#     try:
#         # Only process if AssemblyAI API key is configured
#         if not settings.ASSEMBLYAI_API_KEY:
#             logger.info("AssemblyAI API key not configured - skipping speaker identification")
#             return {}
#         
#         # Create diarization service
#         diarization_service = create_voice_diarization_service(
#             assemblyai_api_key=settings.ASSEMBLYAI_API_KEY,
#             samples_dir=settings.SPEAKER_SAMPLES_DIR,
#             threshold=settings.DIARIZATION_THRESHOLD,
#             min_utterance_ms=settings.MIN_UTTERANCE_MS
#         )
#         
#         # Process clip for speakers
#         speaker_info = diarization_service.process_clip_for_speakers(clip_path)
#         
#         logger.info(f"Speaker identification completed: {speaker_info.get('speakers_detected', [])}")
#         return speaker_info
#         
#     except Exception as e:
#         logger.error(f"Failed to process clip for speakers: {e}")
#         return {}

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
            "upsell_base_sold_items": d.get("upsell_base_sold_items"),
            
            # Upsize fields
            "num_upsize_opportunities": d.get("num_upsize_opportunities"),
            "num_upsize_offers": d.get("num_upsize_offers"),
            "num_upsize_success": d.get("num_upsize_success"),
            "upsize_offered_items": d.get("upsize_offered_items"),
            "upsize_candidate_items": d.get("upsize_candidate_items"),
            "upsize_base_items": d.get("upsize_base_items"),
            "upsize_success_items": d.get("upsize_success_items"),
            "upsize_base_sold_items": d.get("upsize_base_sold_items"),
            
            # Addon fields
            "num_addon_opportunities": d.get("num_addon_opportunities"),
            "num_addon_offers": d.get("num_addon_offers"),
            "num_addon_success": d.get("num_addon_success"),
            "addon_offered_items": d.get("addon_offered_items"),
            "addon_candidate_items": d.get("addon_candidate_items"),
            "addon_base_items": d.get("addon_base_items"),
            "addon_success_items": d.get("addon_success_items"),
            "addon_base_sold_items": d.get("addon_base_sold_items"),
            
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