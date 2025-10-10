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
    print(f"🔍 DEBUG: _process_segment called with segment: start={seg.get('start')}, end={seg.get('end')}, text_length={len(raw)}")
    print(f"🔍 DEBUG: run_id={run_id}, audio_id={audio_id}")
    
    if not raw.strip():
        print(f"🔍 DEBUG: Empty or whitespace-only text, returning empty list")
        return []
    
    print(f"🔍 DEBUG: Calling LLM with model: {settings.STEP1_MODEL}")
    print(f"🔍 DEBUG: Input text length: {len(raw)} characters")
    print(f"🔍 DEBUG: First 200 chars: {raw[:200]}...")
    
    try:
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
        print(f"🔍 DEBUG: LLM response length: {len(text_out)} characters")
        
    except Exception as e:
        print(f"🔍 DEBUG: LLM call failed with exception: {type(e).__name__}: {e}")
        import traceback
        print(f"🔍 DEBUG: LLM exception traceback:")
        traceback.print_exc()
        text_out = ""
    
    parts = [p for p in text_out.split("@#&") if str(p).strip()]
    print(f"🔍 DEBUG: Split into {len(parts)} parts using @#& separator")
    
    if not parts:
        print(f"🔍 DEBUG: No parts found, creating fallback with raw text")
        parts = [json.dumps({"1": raw, "2": "0"})]

    results = []
    seg_dur = max(0.001, float(seg["end"]) - float(seg["start"]))
    slice_dur = seg_dur / len(parts)
    print(f"🔍 DEBUG: Segment duration: {seg_dur}s, slice duration: {slice_dur}s per part")
    
    for i, p in enumerate(parts):
        print(f"🔍 DEBUG: Processing part {i+1}/{len(parts)}: {p[:100]}...")
        d = _json_or_none(p) or {}
        print(f"🔍 DEBUG: Parsed JSON: {d}")
        
        s_rel = float(seg["start"]) + i*slice_dur
        e_rel = float(seg["start"]) + (i+1)*slice_dur
        
        transaction = {
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
        }
        results.append(transaction)
        print(f"🔍 DEBUG: Created transaction {i+1}: complete_order={transaction['meta']['complete_order']}, text_length={len(transaction['meta']['text'])}")
    
    print(f"🔍 DEBUG: _process_segment returning {len(results)} transactions")
    return results


def split_into_transactions(transcript_segments: List[Dict], run_id: str, audio_started_at_iso: str = None, date: str = None, audio_id: str = None) -> List[Dict]:
    print(f"🔍 DEBUG: split_into_transactions called with {len(transcript_segments)} segments")
    print(f"🔍 DEBUG: run_id={run_id}, audio_id={audio_id}")
    
    # Default to current day at 7 AM if not provided
    if audio_started_at_iso is None:
        current_day = dateparse.parse(date).strftime("%Y-%m-%d")
        audio_started_at_iso = f"{current_day}T07:00:00Z"
        print(f"🔍 DEBUG: Generated default timestamp: {audio_started_at_iso}")
    
    actual_audio_start = audio_started_at_iso
    print(f"Using database timestamp: {actual_audio_start}")
    
    # Process each chunk individually for transaction analysis
    print(f"📝 Processing {len(transcript_segments)} chunks individually for transaction analysis")
    
    all_transactions = []
    segments_with_text = 0
    segments_without_text = 0
    segments_processed = 0
    segments_failed = 0
    
    for i, seg in enumerate(transcript_segments):
        print(f"🔍 DEBUG: Processing segment {i+1}/{len(transcript_segments)}")
        print(f"🔍 DEBUG: Segment keys: {list(seg.keys())}")
        print(f"🔍 DEBUG: Segment start: {seg.get('start')}, end: {seg.get('end')}")
        
        if seg.get("text", "").strip():
            segments_with_text += 1
            print(f"🎵 Processing chunk {i+1}/{len(transcript_segments)}: {len(seg['text'])} characters")
            print(f"🔍 DEBUG: First 200 chars: {seg['text'][:200]}...")
            
            # Process this individual chunk for transactions
            try:
                chunk_transactions = _process_segment(seg, run_id, actual_audio_start, audio_id)
                segments_processed += 1
                
                if chunk_transactions:
                    print(f"✅ Chunk {i+1} found {len(chunk_transactions)} transactions")
                    all_transactions.extend(chunk_transactions)
                    print(f"🔍 DEBUG: Total transactions now: {len(all_transactions)}")
                else:
                    print(f"📊 Chunk {i+1} found no transactions")
                    
            except Exception as e:
                segments_failed += 1
                print(f"❌ Error processing segment {i+1}: {e}")
                print(f"🔍 DEBUG: Exception type: {type(e).__name__}")
                import traceback
                print(f"🔍 DEBUG: Full traceback:")
                traceback.print_exc()
        else:
            segments_without_text += 1
            print(f"🔍 DEBUG: Segment {i+1} has no text or empty text")
    
    print(f"📊 Total transactions found across all chunks: {len(all_transactions)}")
    print(f"🔍 DEBUG: Transaction extraction summary:")
    print(f"🔍 DEBUG: - Segments with text: {segments_with_text}")
    print(f"🔍 DEBUG: - Segments without text: {segments_without_text}")
    print(f"🔍 DEBUG: - Segments processed successfully: {segments_processed}")
    print(f"🔍 DEBUG: - Segments failed: {segments_failed}")
    print(f"🔍 DEBUG: - Success rate: {(segments_processed / segments_with_text * 100):.1f}%" if segments_with_text > 0 else "N/A")
    
    return all_transactions


def _iso_from_start(base_iso: str, seconds_from_start: float) -> str:
    base = dateparse.isoparse(base_iso)
    return (base + timedelta(seconds=float(seconds_from_start))).isoformat().replace("+00:00","Z")

def _json_or_none(txt: str) -> Dict[str, Any] | None:
    try:
        result = json.loads(txt.strip())
        print(f"🔍 DEBUG: Successfully parsed JSON: {result}")
        return result
    except Exception as e:
        print(f"🔍 DEBUG: JSON parsing failed for text: {txt[:100]}...")
        print(f"🔍 DEBUG: JSON parsing error: {type(e).__name__}: {e}")
        return None
