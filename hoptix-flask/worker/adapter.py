from __future__ import annotations
import os, json, tempfile, contextlib
from typing import List, Dict, Any
from datetime import datetime, timedelta

import numpy as np
import librosa
from moviepy.editor import VideoFileClip
from openai import OpenAI
from dateutil import parser as dateparse

from config import Settings

_settings = Settings()
client = OpenAI(api_key=_settings.OPENAI_API_KEY)

# ---------- Load menu JSONs (local files) ----------
def _read_json_or_empty(path: str) -> list | dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _build_step2_prompt() -> str:
    # Inline your long prompt (kept exactly as shared) but with placeholders replaced by local JSON
    upselling = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.UPSELLING_JSON))
    upsizing  = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.UPSIZING_JSON))
    addons    = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.ADDONS_JSON))
    items     = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.ITEMS_JSON))
    meals     = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.MEALS_JSON))

    template = """
You are a performance reviewer assessing a Dairy Queen drive-thru operator's handling of an order, focusing on recording statistics about orders, upsizing opportunities, and upselling opportunities.

**Upselling Scenarios**:
<<UPSELLING_JSON>>

**Upsizing Scenarios**:
<<UPSIZING_JSON>>

**Additional Topping Scenarios**:
<<ADDONS_JSON>>

**JSON of Menu Items with Ordered Item Counts, Upselling Opportunities, and Upsizing Opportunities**:
<<ITEMS_JSON>>

**JSON of Menu Meals with Ordered Item Counts, Upselling Opportunities, and Upsizing Opportunities**:
<<MEALS_JSON>>

**Response Guidelines**:
You will be fed a several transcripts, with each transcript potentially with multiple transactions occurring in them. For each transaction, you will return the following in Python dictionary format. Format each entry and key of the dictionary as a single string. Do not add ```python to the front or ``` to the end. Wrap property names in double quotes. Make sure that the python dictionary ends with the right curly bracket, }. Make sure that there are no random line breaks. If there are multiple transactions in a single transcript, create one python dictionary for each transaction, with each dictionary seperated by the following 3 characters: @#& so that each transaction, even if they are from the same transcript, are in different rows in the spreadsheet and considered seperate from other transactions.. Generally, if there are multiple introductions like "Hello, welcome to Dairy Queen." in a transcript, there are multiple transactions in a transcript. Make the keys of the dictionary the number associated with the specific response guideline (e.g. 1 for the first entry, 2 for the second entry, etc.). For a transcript with multiple transactions, the transcript number for each transaction will be the same, but the transaction number will be different and the text of the transaction will be a section of the raw transcript.
Make sure that all integers are formatted as integers, not strings. This is a hard rule and must be followed.
1. Meals and items initially ordered by customer. Make sure this is a single string with no other text than the items ordered. Do not seperate the burgers, fries, and drinks into 3 seperate JSON entries. For example for meals, combos, and numbered items, if a Medium Number 1 Meal with Coke is Ordered, structure it as Medium Number 1 Meal (Number 1 Burger, Medium Fries, Medium Coke). If there are no items ordered, put a 0. Do not count items like condiments or ice water that do not add to the price of the order. Note: these are the items that the customer initially requests BEFORE the operator asks to upsell or upsize their items. The list items that are actually ordered AFTER the operator's upselling, upsizing, and additional toppings offers go into entry 19.
2. Number of Items Ordered. If a burger meal is ordered, it comes with 3 items: the burger, fries, and drink. Make sure that this is a number. Format this as an integer.
3. Number of Chances to Upsell. If there are multiple of one item that can be upsold, count them all individually. For example, 2 Whoppers have 4 chances to upsell to a combo in total, not 2. Format this as an integer.
4. Items that Could be Upsold as a string. If there were no items, write the number 0.
5. Number of Upselling Offers Made. Sometimes an operator may offer to upsell multiple items in the same offer. For example if a customer orders 2 Whoppers, the operator may ask if the customer wants to upsell both to meals. This would count as 2 offers, one for each Whopper. Format this as an integer.
6. Items Successfully Upsold as a string.  If there were no items, write the number 0.
7. Number of Successful Upselling Offers. If an operator offers to upsell multiple items in the same offer, and a customer accepts, then count each item upsized seperately. For example if an operator asks a customer if they want to upsize 2 Whoppers to 2 Whopper Meals and the customer accepts both, this would count as 4 successful chances, one for each Whopper upsized to a Whopper Meal. Format this as an integer.
8. Number of Items for which the Largest Option for that Item was Offerred. If multiple of the largest size of the same item are ordered, like 3 offers to turn an order of fries into an of large fries, each order of large fries is counted seperately, for a total of 3 times the largest option was offered for the fries. Format this as an integer.
9. Number of Chances to Upsize. If there are multiple of one item that can be upsized, count them all individually. For example, 2 orders of fries have 2 chances to upsell to orders of large fries, not 1.
10. Items in Order that Could be Upsized as a string. If there were no items, write the number 0.
11. Number of Upsizing Offers Made. Sometimes an operator may offer to upsize multiple items in the same offer. For example if a customer orders 2 fries, the operator may ask if the customer wants to upsize both to a large. This would count as 2 offers, one for each order of fries. Format this as an integer.
12. Number of Items Successfully Upsized. If an operator offers to upsize multiple items in the same offer, and a customer accepts, then count each item upsized seperately. If 3 orders of fries were upsized, count each one separately, for a total count of 3. Format this as an integer.
13. Items Successfully Upsized as a string. If there were no items, write the number 0.
14. # of Chances to add Additional Toppings. If there are multiple of one item that can have additional toppings, count them all individually. For example, 2 orders of Blizzards have 2 chances to add additional toppings to orders of Blizzards, not 1.
15. Items in Order that could have Additional Toppings added as a string. If there were no items, write the number 0.
16. Number of Additional Toppings Offers Made. Format this as an integer.
17. Number of Successfull additional toppings offers. Format this as an integer.
18. Items that additional toppings were added successfully. If there were no items, write the number 0.
19. Meals and items ordered by customer AFTER upsells, upsizes, and additional toppings offers. Make sure this is a single string with no other text than the items ordered. Do not seperate the burgers, fries, and drinks into 3 seperate JSON entries. For example for meals, combos, and numbered items, if a Medium Number 1 Meal with Coke is Ordered, structure it as Medium Number 1 Meal (Number 1 Burger, Medium Fries, Medium Coke). If there are no items ordered, put a 0. Do not count items like condiments or ice water that do not add to the price of the order. Note: these are the items that the customer initially requests AFTER the operator asks to upsell or upsize their items.
20. Number of Items ordered by customer AFTER upsells, upsizes, and additional toppings offers. Format this as an integer.
21. Structured feedback, as a string with no line breaks. Make sure not to use double quotes inside of the feedback since it is formatted as a string inside of a JSON.
22. List out any and all difficulties, ambiguities, or conflicting instructions encountered when processing the transcript and returning response guidelines 1 through 21
"""
    return (template
            .replace("<<UPSELLING_JSON>>", json.dumps(upselling))
            .replace("<<UPSIZING_JSON>>", json.dumps(upsizing))
            .replace("<<ADDONS_JSON>>", json.dumps(addons))
            .replace("<<ITEMS_JSON>>", json.dumps(items))
            .replace("<<MEALS_JSON>>", json.dumps(meals)))

STEP2_PROMPT = _build_step2_prompt()

INITIAL_PROMPT = """
**Response Guidelines**:
You will be fed a single transcript with potentially multiple transactions occurring. Using your best judgement, split the transcript into multiple transactions. You will return a list of dictionaries, with one dictionary for each transaction. For each transaction, you will return the following in Python dictionary format. Format each entry and key of the dictionary as a single string. Do not add ```python to the front or ``` to the end. Wrap property names in double quotes. Make sure that the python dictionary ends with the right curly bracket, }. Make sure that there are no random line breaks. If there are multiple transactions in a single transcript, create one python dictionary for each transaction, with each dictionary seperated by the folling 3 characters: @#&. Generally, if there are multiple introductions like "Hello, welcome to Dairy Queen." in a transcript, there are multiple transactions in a transcript, but most often there is only 1 transaction in a transcript. Also, if a transcript is spoken in a language other than English, like Spanish, only use English when filling in the columns. Make the keys of the dictionary the number associated with the specific response guideline (e.g. 1 for the first entry, 2 for the second entry, etc.).
1. The full transcript, noting whether the operator or the customer is speaking each line. Seperate each line in the transcript with a new line. Make sure that this contains the entirety of the transcript and DO NOT SUMMARIZE THIS. This is a hard rule.
2. Analyze the transcript and based on the words and coherence of the sentences in the transcript, Return a 1 if this is likely to be a complete transcript and a 0 if this is likely to be a partial transcript with a significant number of words omitted or mis-transcribed. Partial Transcripts often have no items ordered or have the operator asking the customer to wait as the only sentence in the transcript. Also, if a significant amount of the transaction is in a language other than English, like Spanish, return a 0. In addition, a person wants to order an item, but is not able to due to that item being out of stock, and ultimately chooses not to order any items, return a 0. If the customer is picking up a mobile order and not ordering any other items, then the transcript is not complete.
3. Whether this is a mobile order. Write 1 if it is, and 0 of it is not.
4. Whether a coupon is used in the order. Write 1 if it is, and 0 of it is not.
5. Whether the operator asks the customer to wait for some time. Write 1 if it is, and 0 of it is not.
6. Items in Order that Could not be Sold Due to Being Out of Stock. If there were no items, write the number 0.
"""

# ---------- Utilities ----------
@contextlib.contextmanager
def _tmp_audio_from_video(video_path: str):
    tmpdir = tempfile.mkdtemp(prefix="hoptix_asr_")
    out = os.path.join(tmpdir, "audio.mp3")
    clip = VideoFileClip(video_path)
    if clip.audio is None:
        clip.close()
        raise RuntimeError("No audio track in video")
    clip.audio.write_audiofile(out, verbose=False, logger=None)
    duration = float(clip.duration or 0.0)
    clip.close()
    try:
        yield out, duration
    finally:
        with contextlib.suppress(Exception): os.remove(out)
        with contextlib.suppress(Exception): os.rmdir(tmpdir)

def _segment_active_spans(y: np.ndarray, sr: int, window_s: float = 15.0) -> List[tuple[float,float]]:
    # Mirrors your simple “average==0 → silence” logic to carve spans.
    interval = int(sr * window_s)
    idx, removed, prev_active = 0, 0, 0
    begins, ends = [], []
    y_list = y.tolist()
    while idx + interval < len(y_list):
        chunk_avg = float(np.average(y_list[idx: idx + interval]))
        if chunk_avg == 0.0:
            if prev_active == 1:
                ends.append((idx + removed)/sr)
                prev_active = 0
            del y_list[idx: idx+interval]
            removed += interval
        else:
            if prev_active == 0:
                begins.append((idx + removed)/sr)
                prev_active = 1
            idx += interval
    if len(begins) != len(ends):
        ends.append((len(y_list)+removed)/sr)
    return list(zip(begins, ends))

def _parse_dt_file_timestamp(s3_key: str) -> str:
    """
    Parse DT_File timestamp from S3 key.
    Format: DT_File{YYYYMMDDHHMMSSFFF}
    Example: DT_File20250817170001000 -> 2025-08-17T17:00:01.000Z
    """
    import re
    import datetime
    
    # Extract filename from S3 key path
    filename = s3_key.split('/')[-1]
    
    # Match DT_File format: DT_File + 17 digits (YYYYMMDDHHMMSSFFF)
    match = re.match(r'DT_File(\d{17})', filename)
    if not match:
        # Fallback: return current time if format doesn't match
        return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")
    
    timestamp_str = match.group(1)
    
    # Parse: YYYYMMDDHHMMSSFFF
    year = int(timestamp_str[0:4])
    month = int(timestamp_str[4:6])
    day = int(timestamp_str[6:8])
    hour = int(timestamp_str[8:10])
    minute = int(timestamp_str[10:12])
    second = int(timestamp_str[12:14])
    millisecond = int(timestamp_str[14:17])
    
    # Create datetime object
    dt = datetime.datetime(year, month, day, hour, minute, second, 
                          millisecond * 1000, datetime.timezone.utc)
    
    return dt.isoformat().replace("+00:00","Z")

def _iso_from_start(base_iso: str, seconds_from_start: float) -> str:
    base = dateparse.isoparse(base_iso)
    return (base + timedelta(seconds=float(seconds_from_start))).isoformat().replace("+00:00","Z")

def _json_or_none(txt: str) -> Dict[str, Any] | None:
    try:
        return json.loads(txt.strip())
    except Exception:
        return None

# ---------- 1) TRANSCRIBE (extract spans, per‑span ASR) ----------
def transcribe_video(local_path: str) -> List[Dict]:
    segs: List[Dict] = []
    with _tmp_audio_from_video(local_path) as (audio_path, duration):
        y, sr = librosa.load(audio_path, sr=None)
        spans = _segment_active_spans(y, sr, 15.0) or [(0.0, duration)]
        for i, (b, e) in enumerate(spans):
            # safer subclip render
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                tmp_audio = tf.name
            # Ensure end time doesn't exceed video duration
            end_time = min(int(e+1), duration)
            clip = VideoFileClip(local_path).subclip(int(b), end_time)
            clip.audio.write_audiofile(tmp_audio, verbose=False, logger=None)
            clip.close()

            with open(tmp_audio, "rb") as af:
                try:
                    txt = client.audio.transcriptions.create(
                        model=_settings.ASR_MODEL,
                        file=af,
                        response_format="text",
                        temperature=0.001,
                        prompt="Label each line as Operator: or Customer: where possible."
                    )
                    text = str(txt)
                except Exception as ex:
                    print("ASR error:", ex)
                    text = ""
            with contextlib.suppress(Exception): os.remove(tmp_audio)

            segs.append({"start": float(b), "end": float(e), "text": text})
    return segs

# ---------- 2) SPLIT (Step‑1 prompt per segment, preserve your @#& format) ----------
def split_into_transactions(transcript_segments: List[Dict], video_started_at_iso: str, s3_key: str = None) -> List[Dict]:
    # Use actual video timestamp from filename if available, otherwise use database timestamp
    if s3_key:
        actual_video_start = _parse_dt_file_timestamp(s3_key)
        print(f"Using video timestamp from filename: {actual_video_start}")
    else:
        actual_video_start = video_started_at_iso
        print(f"Using database timestamp: {actual_video_start}")
    
    results: List[Dict] = []
    for seg in transcript_segments:
        raw = seg.get("text","") or ""
        if not raw.strip():
            continue
        resp = client.responses.create(
            model=_settings.STEP1_MODEL,
            input=[{
                "role":"user",
                "content":[
                    {"type":"input_text","text": INITIAL_PROMPT},
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
        
        parts = [p for p in text_out.split("@#&") if str(p).strip()]
        if not parts:
            parts = [json.dumps({"1": raw, "2": "0"})]

        seg_dur = max(0.001, float(seg["end"]) - float(seg["start"]))
        slice_dur = seg_dur / len(parts)
        for i, p in enumerate(parts):
            d = _json_or_none(p) or {}
            s_rel = float(seg["start"]) + i*slice_dur
            e_rel = float(seg["start"]) + (i+1)*slice_dur
            results.append({
                "started_at": _iso_from_start(actual_video_start, s_rel),
                "ended_at":   _iso_from_start(actual_video_start, e_rel),
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
                    "video_start_seconds": s_rel,
                    "video_end_seconds": e_rel,
                    "s3_key": s3_key or "",
                    "segment_index": i,
                    "total_segments_in_video": len(parts)
                }
            })
    return results

# ---------- 3) GRADE (Step‑2 prompt per transaction, return ALL columns) ----------
def _map_step2_to_grade_cols(step2_obj: Dict[str,Any], tx_meta: Dict[str,Any]) -> Dict[str,Any]:
    """Map your numbered keys to explicit grade columns."""
    # Defaults
    def _ii(x, default=0): 
        try: return int(x)
        except: return default

    return {
        # Colab Step‑2 basic flags from Step‑1 meta for completeness
        "complete_order": _ii(tx_meta.get("complete_order", 0)),
        "mobile_order":   _ii(tx_meta.get("mobile_order", 0)),
        "coupon_used":    _ii(tx_meta.get("coupon_used", 0)),
        "asked_more_time":_ii(tx_meta.get("asked_more_time", 0)),
        "out_of_stock_items": tx_meta.get("out_of_stock_items","0"),

        # Core opportunity/offer fields (1..19,20,21,22) – mapped to snake_case
        "items_initial":              step2_obj.get("1", "0"),
        "num_items_initial":          _ii(step2_obj.get("2", 0)),
        "num_upsell_opportunities":   _ii(step2_obj.get("3", 0)),
        "items_upsellable":           step2_obj.get("4", "0"),
        "num_upsell_offers":          _ii(step2_obj.get("5", 0)),
        "items_upsold":               step2_obj.get("6", "0"),
        "num_upsell_success":         _ii(step2_obj.get("7", 0)),
        "num_largest_offers":         _ii(step2_obj.get("8", 0)),
        "num_upsize_opportunities":   _ii(step2_obj.get("9", 0)),
        "items_upsizeable":           step2_obj.get("10", "0"),
        "num_upsize_offers":          _ii(step2_obj.get("11", 0)),
        "num_upsize_success":         _ii(step2_obj.get("12", 0)),
        "items_upsize_success":       step2_obj.get("13", "0"),
        "num_addon_opportunities":    _ii(step2_obj.get("14", 0)),
        "items_addonable":            step2_obj.get("15", "0"),
        "num_addon_offers":           _ii(step2_obj.get("16", 0)),
        "num_addon_success":          _ii(step2_obj.get("17", 0)),
        "items_addon_success":        step2_obj.get("18", "0"),
        "items_after":                step2_obj.get("19", "0"),
        "num_items_after":            _ii(step2_obj.get("20", 0)),
        "feedback":                   step2_obj.get("21", ""),
        "issues":                     step2_obj.get("22", ""),

        # Extras used in your Colab
        "reasoning_summary":          step2_obj.get("24. Reasoning Summary", ""),
        "gpt_price":                  step2_obj.get("25. GPT Price", 0),
        "video_file_path":            step2_obj.get("28. Video File Path", ""),
        "video_link":                 step2_obj.get("29. Google Drive Video Link", ""),
    }

def grade_transactions(transactions: List[Dict]) -> List[Dict]:
    graded: List[Dict] = []
    for tx in transactions:
        transcript = (tx.get("meta") or {}).get("text","")
        if not transcript.strip():
            # produce an empty row but keep columns
            base = _map_step2_to_grade_cols({}, tx.get("meta") or {})
            graded.append({
                # 4 booleans + score (for backwards compatibility)
                "upsell_possible": False,
                "upsell_offered":  False,
                "upsize_possible": False,
                "upsize_offered":  False,
                "score": 0.0,
                "details": base,
                "transcript": "",     # Empty transcript
                "gpt_price": 0.0      # No cost for empty
            })
            continue

        # Run Step‑2
        prompt = STEP2_PROMPT + "\n\nProcess this transcript:\n" + transcript
        try:
            resp = client.responses.create(
                model=_settings.STEP2_MODEL,
                include=["reasoning.encrypted_content"],
                input=[{"role":"user","content":[{"type":"input_text","text": prompt}]}],
                store=False,
                text={"format":{"type":"text"}},
                reasoning={"effort":"high","summary":"detailed"},
            )
            raw = resp.output[1].content[0].text if hasattr(resp,"output") else "{}"
            print(f"\n=== STEP 2 (Grading) RAW OUTPUT ===")
            print(f"Input transcript: {transcript[:200]}...")
            print(f"Raw LLM response: {raw}")
            print("=" * 50)
            
            parsed = _json_or_none(raw) or {}
            print(f"Parsed JSON: {parsed}")
            
            # Calculate GPT price from API usage
            gpt_price = 0.0
            if hasattr(resp, 'usage'):
                # OpenAI o3 pricing: $2/1k input tokens, $8/1k output tokens
                input_cost = (resp.usage.input_tokens / 1000) * 2.0
                output_cost = (resp.usage.output_tokens / 1000) * 8.0
                gpt_price = input_cost + output_cost
                print(f"GPT Price: ${gpt_price:.6f} (input: {resp.usage.input_tokens} tokens, output: {resp.usage.output_tokens} tokens)")
            
            print("=" * 50)
        except Exception as ex:
            print("Step‑2 error:", ex)
            parsed = {}
            gpt_price = 0.0

        details = _map_step2_to_grade_cols(parsed, tx.get("meta") or {})
        print(f"Mapped details: {details}")
        print("=" * 50)

        # Derive simple booleans + score (kept for backward compatibility)
        upsell_possible = int(parsed.get("3", 0)) > 0
        upsell_offered  = int(parsed.get("5", 0)) > 0
        upsize_possible = int(parsed.get("9", 0)) > 0
        upsize_offered  = int(parsed.get("11",0)) > 0

        # score: if present, else a light heuristic
        score = parsed.get("score", None)
        if score is None:
            try:
                total_ops = int(parsed.get("3",0)) + int(parsed.get("9",0))
                total_off = int(parsed.get("5",0)) + int(parsed.get("11",0))
                score = float(total_off) / float(total_ops) if total_ops > 0 else 0.0
            except Exception:
                score = 0.0

        graded.append({
            "upsell_possible": bool(upsell_possible),
            "upsell_offered":  bool(upsell_offered),
            "upsize_possible": bool(upsize_possible),
            "upsize_offered":  bool(upsize_offered),
            "score":           float(score),
            "details":         details,
            "transcript":      transcript,  # Add raw transcript
            "gpt_price":       gpt_price    # Add calculated price
        })
    return graded