from typing import List, Dict, Any
from openai import OpenAI
import json
from datetime import timedelta
from dateutil import parser as dateparse
from concurrent.futures import ThreadPoolExecutor
from config import Settings
from config import Prompts

settings = Settings()
prompts = Prompts()
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _process_segment(seg: Dict, run_id: str, actual_audio_start: str, audio_id: str) -> List[Dict]:
    """Process a single transcript segment"""
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
        reasoning={"effort":"high","summary":"detailed" },
    )
    text_out = resp.output[1].content[0].text if hasattr(resp, "output") else ""
    print(f"\n=== STEP 1 (Transaction Splitting) RAW OUTPUT ===")
    print(f"Input transcript: {raw[:200]}...")
    print(f"Raw LLM response: {text_out}")
    print("=" * 50)
    
    parts = [p for p in text_out.split("@#&") if str(p).strip()]
    if not parts:
        parts = [json.dumps({"1": raw, "2": "0"})]

    results = []
    seg_dur = max(0.001, float(seg["end"]) - float(seg["start"]))
    slice_dur = seg_dur / len(parts)
    for i, p in enumerate(parts):
        d = _json_or_none(p) or {}
        s_rel = float(seg["start"]) + i*slice_dur
        e_rel = float(seg["start"]) + (i+1)*slice_dur
        results.append({
            "run_id": run_id,
            "audio_id": audio_id,
            "started_at": _iso_from_start(actual_audio_start, s_rel),
            "ended_at":   _iso_from_start(actual_audio_start, e_rel),
            "tx_range": f'["{_iso_from_start(actual_audio_start, s_rel)}","{_iso_from_start(actual_audio_start, e_rel)}")',
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
                "total_segments_in_video": len(parts)
            }
        })
    return results


def split_into_transactions(transcript_segments: List[Dict], run_id: str, audio_started_at_iso: str = None, date: str = None, audio_id: str = None) -> List[Dict]:
    # Default to current day at 7 AM if not provided
    if audio_started_at_iso is None:
        current_day = dateparse.parse(date).strftime("%Y-%m-%d")
        audio_started_at_iso = f"{current_day}T07:00:00Z"
    
    actual_audio_start = audio_started_at_iso
    print(f"Using database timestamp: {actual_audio_start}")
    
    # Process each chunk individually for transaction analysis
    print(f"📝 Processing {len(transcript_segments)} chunks individually for transaction analysis")
    
    all_transactions = []
    
    for i, seg in enumerate(transcript_segments):
        if seg.get("text", "").strip():
            print(f"🎵 Processing chunk {i+1}/{len(transcript_segments)}: {len(seg['text'])} characters")
            
            # Process this individual chunk for transactions
            chunk_transactions = _process_segment(seg, run_id, actual_audio_start, audio_id)
            
            if chunk_transactions:
                print(f"✅ Chunk {i+1} found {len(chunk_transactions)} transactions")
                all_transactions.extend(chunk_transactions)
            else:
                print(f"📊 Chunk {i+1} found no transactions")
    
    print(f"📊 Total transactions found across all chunks: {len(all_transactions)}")
    
    return all_transactions


def _iso_from_start(base_iso: str, seconds_from_start: float) -> str:
    base = dateparse.isoparse(base_iso)
    return (base + timedelta(seconds=float(seconds_from_start))).isoformat().replace("+00:00","Z")

def _json_or_none(txt: str) -> Dict[str, Any] | None:
    try:
        return json.loads(txt.strip())
    except Exception:
        return None
