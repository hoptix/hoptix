from typing import List, Dict, Any
from datetime import datetime

from config import Settings, Prompts
from openai import OpenAI
import json
import os
from typing import Dict, Any, List
from utils.helpers import iso_from_start, iso_or_die
from utils.helpers import json_or_none
from concurrent.futures import ThreadPoolExecutor
from services.database import Supa
settings = Settings()
prompts = Prompts()
client = OpenAI(api_key=settings.OPENAI_API_KEY)
db = Supa()


def split_into_transactions(transcript_segments: List[Dict], date: str, audio_id: str, run_id: str, audio_started_at_iso: str = "10:00:00Z", test_first_segment: bool = True) -> List[Dict]:
    # Anchor all transaction times strictly to the audio's database start time
    print(f"Using database timestamp: {date}T{audio_started_at_iso}")
    
    # Test mode: process first segment only first
    if test_first_segment and transcript_segments:
        print(f"🧪 TEST MODE: Processing first segment only ({len(transcript_segments)} total segments)")
        first_segment = transcript_segments[0]
        print(f"First segment: {first_segment.get('text', '')[:100]}...")
        
        # Process first segment
        first_transactions = _process_segment(first_segment, date, audio_id, run_id, audio_started_at_iso)
        print(f"✅ First segment processed: {len(first_transactions)} transactions")
        
        if len(transcript_segments) == 1:
            return first_transactions
        
        # Ask user if they want to continue with parallel processing
        print(f"🔄 Proceeding with parallel processing of remaining {len(transcript_segments) - 1} segments...")
    
    # Process segments in parallel with controlled concurrency
    with ThreadPoolExecutor(max_workers=10) as executor:  # Reduced to avoid rate limits
        futures = [
            executor.submit(_process_segment, seg, date, audio_id, run_id, audio_started_at_iso) 
            for seg in transcript_segments
        ]
        
        # Collect all results and flatten
        all_transactions = []
        for future in futures:
            segment_transactions = future.result()
            if segment_transactions:  # Filter out None/empty results
                all_transactions.extend(segment_transactions)
    
    return all_transactions


def upload_transactions_to_database(transactions: List[Dict], batch_size: int = 30) -> List[Dict]:
    """Upload transactions to database in batches and return all uploaded transactions with IDs."""
    if not transactions:
        return []
    
    all_uploaded_transactions = []
    total_batches = (len(transactions) + batch_size - 1) // batch_size
    
    print(f"📤 Uploading {len(transactions)} transactions in {total_batches} batches of {batch_size}")
    
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"📤 Uploading batch {batch_num}/{total_batches} ({len(batch)} transactions)")
        
        try:
            # Upload batch to database
            uploaded_batch = db.upsert_transactions(batch)
            all_uploaded_transactions.extend(uploaded_batch)
            print(f"✅ Successfully uploaded batch {batch_num}/{total_batches}")
            
        except Exception as e:
            print(f"❌ Failed to upload batch {batch_num}/{total_batches}: {e}")
            # Continue with next batch instead of failing completely
            continue
    
    print(f"🎉 Completed uploading {len(all_uploaded_transactions)} transactions in {total_batches} batches")
    return all_uploaded_transactions

def _process_segment(seg: Dict, date: str, audio_id: str, run_id: str, audio_started_at_iso: str) -> List[Dict]:
    """Process a single transcript segment and return all transactions from it."""
    raw = seg.get("text","") or ""
    if not raw.strip():
        return []
    
    resp = client.responses.create(
        model=settings.STEP1_MODEL,
        input=[{
            "role":"user",
            "content":[
                {"type":"input_text","text": prompts.INITIAL_PROMPT},
                {"type":"input_text","text": "This is the transcript of the call:\n"+raw}
            ]
        }],
        store=False,
        text={"format":{"type":"text"}},
        reasoning={"effort":"high","summary":"detailed"},
    )
    text_out = resp.output[1].content[0].text if hasattr(resp, "output") else ""
    print(f"\n=== STEP 1 (Transaction Splitting) RAW OUTPUT ===")
    print(f"Input transcript: {raw[:200]}...")
    print(f"Raw LLM response: {text_out}")
    print("=" * 50)

    # Normalize LLM output: it may be a JSON array or a delimiter-separated string
    normalized_parts = None
    try:
        maybe_json = json.loads(text_out)
        if isinstance(maybe_json, list) and len(maybe_json) > 0:
            # Use list of dicts directly
            normalized_parts = maybe_json
    except Exception:
        normalized_parts = None

    if normalized_parts is None:
        # Fallback to delimiter-based splitting
        split_parts = [p for p in text_out.split("@#&") if str(p).strip()]
        if not split_parts:
            # Ultimate fallback: single default part
            normalized_parts = [{"1": raw, "2": "0"}]
        else:
            normalized_parts = split_parts

    # Process all parts from this segment
    segment_transactions = []
    seg_dur = max(0.001, float(seg["end"]) - float(seg["start"]))
    slice_dur = seg_dur / max(1, len(normalized_parts))
    
    for i, p in enumerate(normalized_parts):
        # Ensure we have a dict for downstream access
        if isinstance(p, dict):
            d = p
        else:
            d = json_or_none(p) or {"1": raw, "2": "0"}
        s_rel = float(seg["start"]) + i*slice_dur
        e_rel = float(seg["start"]) + (i+1)*slice_dur
        segment_transactions.append({
            "audio_id": audio_id, 
            "run_id": run_id,
            "started_at": iso_from_start(f"{date}T{audio_started_at_iso}", s_rel),
            "ended_at":   iso_from_start(f"{date}T{audio_started_at_iso}", e_rel),
            "tx_range": [iso_from_start(f"{date}T{audio_started_at_iso}", s_rel), iso_from_start(f"{date}T{audio_started_at_iso}", e_rel)],
            "kind": "order",
            "meta": {
                "text": d.get("1", raw),
                "complete_order": int(str(d.get("2","0")) or "0"),
                "mobile_order": int(str(d.get("3","0")) or "0"),
                "coupon_used": int(str(d.get("4","0")) or "0"),
                "asked_more_time": int(str(d.get("5","0")) or "0"),
                "out_of_stock_items": d.get("6","0"),
                "step1_raw": p,
                # Additional timing metadata
                "audio_start_seconds": s_rel,
                "audio_end_seconds": e_rel,
                "segment_index": i,
                "total_segments_in_audio": len(normalized_parts)
            }
        })
    
    return segment_transactions
