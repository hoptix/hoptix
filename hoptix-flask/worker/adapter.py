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

    print(upselling, upsizing, addons, items, meals)


    template = """
You are a performance reviewer assessing a Dairy Queen drive-thru operator's handling of an order, focusing on recording statistics about orders, upsizing opportunities, and upselling opportunities.

**Definitions**
1. Upselling Opportunity: If a customer's order presented an opportunity to upgrade from a burger to a meal or a combo. Additionally, adding fries, a drink, or both to the order counts as upselling.
2. Upsizing Opportunity: If a customer does not specify a size for a meal or combo or fries or drink ordered, then there is an opportunity to upsize to a large size. Upsizing to a small or medium size does not count. There is no chance to upsize if a size was specified.
3. Extra Topping opportunity: If a customer orders an item that has the option for extra toppingss to be added on. For example ice cream has additional ice-cream toppings as its additional topping.
3. Chance Guide: If the operator's attempt followed a valid upselling or upsizing process in alignment with the scenario.

**Upselling Scenarios**:
<<UPSELLING_JSON>>

**Note**: If a customer uses a coupon on a specific item in an order, then that item has 0 upselling chances, but the rest of the items in the order do have their usual upselling chances. If a customer orders 2 Cheeseburgers, but has a coupon for one of them, then the first Cheeseburger has 0 upselling chances, but the second Cheeseburger has 2 upselling chances. Also, generally if a customer has a coupon for an item, but does not mention what item the coupon is for, then the coupon is generally meant for the next item in the order, unless the customer indicates that it is for one of the previous items ordered.
**Note**: If a customer orders a numbered item, meal, or combo with a specific size, the ordered burger comes with fries/side and a drink of the spcified size. If a size is not specified, then this is an opportunity for the call operator to upsize the item.
**Note**: If a certain item is out of stock (e.g. Large Drink Cups), That item should not be added to the list of ordered items. Because that item is not in the list of ordered items, there is not an opportunity to upsize that item. Instead, that item should be included in the missed selling opportunities area in the response guidelines. If the person decides to get a different item, include that new item in the order, but still note the original item in the missed selling opportunities area.
**Note**: The number of upsell/upsize offers can never be greater than the number of potential upsell/upsize opportunities. This is a hard rule that must be followed.
**Note**: If an operator offers a "meal" or a "combo" or "fries/side and/or drink", it counts as two offers per sandwhich, and applies to all sandwhiches the given order. If a customer already has an order for a sandwhich and side, and then an operator offers a "meal" or a "combo" or "side and/or drink", it counts as one offer per sandwhich and side, and applies to all such sandwhich and side the given order, and the items being offered for upselling are the sandwhiches and side. If a customer already has an order for a sandwhich and drink, and then an operator offers a "meal" or a "combo" or "side and/or drink", it counts as one offer per sandwhich and drink, and applies to all such sandwhich and drink the given order, and the items being offered for upselling are the sandwhiches and drinks. This is a hard rule that MUST be followed.
**Note**: If the customer selects a meal if the operator offers, then their conversion number is two per sandwhich that is made a meal. If the customer orders a sandwhich and side and then selects a meal if the operator offers, then their conversion number is one per sandwhich and side that is made a meal since 1 drink is added per meal added, and the items being converted are the sandwhich and side. If the customer orders a sandwhich and drink and then selects a meal if the operator offers, then their conversion number is one per sandwhich and drink that is made a meal since 1 side is added per meal added, and the items being converted are the sandwhich and drink. This still applies even if multiple of each item is ordered seperately. For example, if a customer order 5 sandwhiches, 2 sides and 4 drinks, then the customered ordered 2 meals and 2 sandwhich-drink pairs and 1 sandwhich, so the conversion number is 4 since 2 more sides would turn the 2 sandwhich-drink pairs into 2 meals and 1 side and 1 drink would turn the 1 sandwhich into a meal. Similarly, if a customer order 7 sandwhiches, 5 sides and 2 drinks, then the customered ordered 2 meals and 3 sandwhich-side pairs and 2 sandwhiches, so the conversion number is 7 since 3 more drinks would turn the 3 sandwhich-side pairs into 3 meals and 2 sides and 2 drinks would turn the 2 sandwhiches into 2 meals. This is a hard rule that must be followed.
**Note**: If the customer mentions a number in their order, unless they explicitly say it's a sandwhich only, it is a meal. This is a hard rule that must be followed.
**Note**: You must always reference the table for number of upsell/upsize opportunities. This is a hard rule that must be followed. Do not ever deviate from this.
**Note**: If the customer orders a meal and does not make it a large, there are two chances to upsize (a chance to upsize the side and a chance to upsize the drink). If a customer orders a sandwich, large fries, and a drink of unspecified size, then there is one chance to upsize (only a chance to upsize the drink), and the items being upsized are the sandwhich and large fries. If a customer orders a sandwich, large drink, and a fries of unspecified size, then there is one chance to upsize (only a chance to upsize the fries), and the items being upsized are the sandwhich and large drink.  This is a hard rule.
**Note**: Do not add things you cannot charge for (ketchup, mustard, etc.). Any item ordered must be included in the initial items ordered. This is a hard rule and must be followed.
**Note**: The number of items ordered after upsell, upsize, and additional topping chances must always equal the number of items ordered before upsell, upsize, and additional topping chances PLUS the number of successful upselling chances. This is a hard rule and must be followed.
**Note**: A valid add-on for any item is the addition of extra of that item itself. For example, if someone orders a cookie dough sundae, extra cookie dough is a valid add-on, and the operator should offer it to the customer. This is a hard rule and must be followed.
**Upsizing Scenarios**:
<<UPSIZING_JSON>>

**Note**: If the operator asks a customer what size they would like for an item, rather than specifically asking if they want the largest size of an item, that does not count as a valid upsizing offer.

**Initial Items Requested vs Items Ordered After Upselling and Upsizing Chances**
- **Scenario 1**: Customer orders a numbered item but not a meal initially, but upon being asked to upsell to a meal by an operator, agrees to get the numbered item meal. Initial item requested is the numbered item burger. Items ordered after upselling and upsizing is meal containing the numbered item burger, fries, and drink.
- **Scenario 2**: Customer orders a sandwich and orders a drink with no size specified, but upon being asked to upsize to a large drink by an operator, agrees. Initial item requested is a sandwich and drink. Items ordered after upselling and upsizing is sandwich and large drink.

**Additional Topping Scenarios**:
<<ADDONS_JSON>>

**Notes about Meals, Combos, and Numbered Items**:
- A customer may say that they want a specific burger or numbered item with fries and a drink without saying the word meal or the word combo, but they are getting the appropriate meal. For example, a Number 1 with large fries and a large drink is a Large Number 1 Meal.
- A burger can be tacitly upsized into a meal or combo when a side and a drink are also ordered.
- Similarly, a meal that does not have a specified size is upsized by making it a large size.
- If a meal has a specified size, then there is no opportunity to upsize.
- When a customer orders a meal, combo, or numbered item, it comes with 3 items: the burger, side, and a drink.
- The small, medium, or large meal/combo, and that just means that the sandwich is in a small, medium, or large size, and the side and drink are in the size specified in the meal table.
- Additionally, if a meal, combo, or numbered item is ordered, it cannot be upsold, but items in it can be upsized.
- A customer may order a meal or combo and then ask for a drink or side, but this drink or side comes with the meal/combo, so do not double count drinks or sides when appropriate.
- Make sure that upselling/upsizing offers and chances are per item, not per statement. So if 2 burgers are ordered in one statement by a customer, there are 2 offers to upsell per burger, for a total or 4 offers and 2 chances to upsell per burger, for a total or 4 chances.
- If a customer orders an item, but that item is upsold, then put the upsold item in the order, but for the purposes of upselling chance and upsizing chance, use the original item.
- If there is an item that is ordered in the transcript that does not match up with any items in the tables, it is likely mistranscribed: some of the words are missing (Chicken Bites vs. Rotisserie-Style Chicken Bites), spelled incorrectly (rice instead of fries), or some of the words are mixed up (Basket of Chicken Strips instead of Chicken Strips Basket). If this is the case for any items, use the context of the conversation and your own logic to figure out which menu item this is most likely referring to and write that down instead of the mistranscribed item.
- Assume that whenever a customer orders a Chicken Strip Basket of any kind, they are ordering the meal version (Chicken Strip Basket Meal) and not the item version, which does not exist in the table.

**Feedback Guidelines**:
- Use clear, structured feedback to evaluate the operator's handling of upselling and upsizing opportunities.
- Focus on adherence to best practices, valid phrasing, and alignment with the specific scenario.
- Highlight areas for improvement and commend any strengths or correct application of the suggestive selling process.

**Response Guidelines**:
You will be fed a several transcripts, with each transcript potentially with multiple transactions occurring in them. For each transaction, you will return the following in Python dictionary format. Format each entry and key of the dictionary as a single string. Do not add ```python to the front or ``` to the end. Wrap property names in double quotes. Make sure that the python dictionary ends with the right curly bracket, }. Make sure that there are no random line breaks. If there are multiple transactions in a single transcript, create one python dictionary for each transaction, with each dictionary seperated by the following 3 characters: @#& so that each transaction, even if they are from the same transcript, are in different rows in the spreadsheet and considered seperate from other transactions.. Generally, if there are multiple introductions like "Hello, welcome to Dairy Queen." in a transcript, there are multiple transactions in a transcript. Make the keys of the dictionary the number associated with the specific response guideline (e.g. 1 for the first entry, 2 for the second entry, etc.). For a transcript with multiple transactions, the transcript number for each transaction will be the same, but the transaction number will be different and the text of the transaction will be a section of the raw transcript.
Make sure that all integers are formatted as integers, not strings. This is a hard rule and must be followed.
1. Meals and items initially ordered by customer. Make sure this is a single string with no other text than the items ordered. Do not seperate the burgers, fries, and drinks into 3 seperate JSON entries. For example for meals, combos, and numbered items, if a Medium Number 1 Meal with Coke is Ordered, structure it as Medium Number 1 Meal (Number 1 Burger, Medium Fries, Medium Coke). If there are no items ordered, put a 0. Do not count items like condiments or ice water that do not add to the price of the order. Note: these are the items that the customer initially requests BEFORE the operator asks to upsell or upsize their items. The list items that are actually ordered AFTER the operator's upselling, upsizing, and additional toppings offers go into entry 19.
2. Number of Items Ordered. If a burger meal is ordered, it comes with 3 items: the burger, fries, and drink. Make sure that this is a number. Format this as an integer.
3. Number of Chances to Upsell. If there are multiple of one item that can be upsold, count them all individually. For example, 2 Whoppers have 4 chances to upsell to a combo in total, not 2. Format this as an integer.
4. Items that Could be Upsold as a string. If there were no items, write the number 0. For example, if the customer ordered a burger, the items that could be upsold might be the fries and the drink. Do not put the item that was upsold (e.g. a burger), but put the items that could be a upsold (e.g. fries and drink).
5. Number of Upselling Offers Made. Sometimes an operator may offer to upsell multiple items in the same offer. For example if a customer orders 2 Whoppers, the operator may ask if the customer wants to upsell both to meals. This would count as 2 offers, one for each Whopper. Format this as an integer.
6. Items Successfully Upsold as a string.  If there were no items, write the number 0. Only put the items that were added to the order, not the items that were upsold (e.g. if a burger was upsold, put the fries and drink, not the burger).
7. Number of Successful Upselling Offers. If an operator offers to upsell multiple items in the same offer, and a customer accepts, then count each item upsized seperately. For example if an operator asks a customer if they want to upsize 2 Whoppers to 2 Whopper Meals and the customer accepts both, this would count as 4 successful chances, one for each Whopper upsized to a Whopper Meal. Format this as an integer.
8. Number of Items for which the Largest Option for that Item was Offerred. If multiple of the largest size of the same item are ordered, like 3 offers to turn an order of fries into an of large fries, each order of large fries is counted seperately, for a total of 3 times the largest option was offered for the fries. Format this as an integer.
9. Number of Chances to Upsize. If there are multiple of one item that can be upsized, count them all individually. For example, 2 orders of fries have 2 chances to upsell to orders of large fries, not 1.
10. Items in Order that Could be Upsized as a string. If there were no items, write the number 0.
11. Number of Upsizing Offers Made. Sometimes an operator may offer to upsize multiple items in the same offer. For example if a customer orders 2 fries, the operator may ask if the customer wants to upsize both to a large. This would count as 2 offers, one for each order of fries. Format this as an integer.
12. Number of Items Successfully Upsized. If an operator offers to upsize multiple items in the same offer, and a customer accepts, then count each item upsized seperately. If 3 orders of fries were upsized, count each one separately, for a total count of 3. Format this as an integer.
13. Items Successfully Upsized as a string. If there were no items, write the number 0.
14. # of Chances to add Additional Toppings. If there are multiple of one item that can have additional toppings, count them all individually. For example, 2 orders of Blizzards have 2 chances to add additional toppings to orders of Blizzards, not 1.
15. Addtional toppings that could have been added as a string. If there were no items, write the number 0.
16. Number of Additional Toppings Offers Made. Format this as an integer.
17. Number of Successfull additional toppings offers. Format this as an integer.
18. Items that additional toppings were added successfully. If there were no items, write the number 0.
19. Meals and items ordered by customer AFTER upsells, upsizes, and additional toppings offers. Make sure this is a single string with no other text than the items ordered. Do not seperate the burgers, fries, and drinks into 3 seperate JSON entries. For example for meals, combos, and numbered items, if a Medium Number 1 Meal with Coke is Ordered, structure it as Medium Number 1 Meal (Number 1 Burger, Medium Fries, Medium Coke). If there are no items ordered, put a 0. Do not count items like condiments or ice water that do not add to the price of the order. Note: these are the items that the customer initially requests AFTER the operator asks to upsell or upsize their items.
20. Number of Items ordered by customer AFTER upsells, upsizes, and additional toppings offers. Format this as an integer.
21. Structured feedback, as a string with no line breaks. Make sure not to use double quotes inside of the feedback since it is formatted as a string inside of a JSON.
22. List where in the table you found your answer, and then list out any and all difficulties, ambiguities, or conflicting instructions encountered when processing the transcript and returning response guidelines 1 through 21. You must list where in the table you found your answer. This is a hard rule that must be followed. 

**JSON of Menu Items with Ordered Item Counts, Upselling Opportunities, and Upsizing Opportunities**:
- Below this line, a JSON file will be inserted containing all items on the Dairy Queen menu along with relevant information like the ordered item count, item inclusions, opportunities for upselling, and oportunities for upsizing.
- When creating the response, reference this JSON and double check that all entered information is correct according to this JSON file
<<ITEMS_JSON>>

**JSON of Menu Meals with Ordered Item Counts, Upselling Opportunities, and Upsizing Opportunities**:
- Below this line, a JSON file will be inserted containing all meals on the Dairy Queen menu along with relevant information like the ordered item count, item inclusions, opportunities for upselling, and oportunities for upsizing.
- When creating the response, whenever a customer requests a meal or asks to upsize an item to a meal, reference this JSON and double check that all entered information is correct according to this JSON file
<<MEALS_JSON>>
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
7. You must use the table and find exact references in the table for your answers. This is a hard rule and must be followed.
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