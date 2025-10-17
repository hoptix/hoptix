# grades transcations using openai 

from config import Prompts, Settings
from openai import OpenAI
import json
import os
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from utils.helpers import ii, parse_json_field, json_or_none, read_json_or_empty, calculate_gpt_price, calculate_gpt_price_batch
from services.database import Supa


settings = Settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

prompts = Prompts()
db = Supa() 

def grade_transactions(transactions: List[Dict], location_id: str, testing=True) -> List[Dict]:
    # Build prompt once (shared across all transactions)
    step2_prompt = build_step2_prompt(location_id)
    
    print(f"🎯 Starting to grade {len(transactions)} transactions")
    
    # Parallelize transaction grading
    with ThreadPoolExecutor(max_workers=10) as executor:
        graded = list(executor.map(
            lambda tx: _grade_transaction(tx, location_id, step2_prompt, testing),
            transactions
        ))
    
    # Filter out any None results and log issues
    valid_grades = [g for g in graded if g is not None]
    failed_count = len(graded) - len(valid_grades)
    
    if failed_count > 0:
        print(f"⚠️  WARNING: {failed_count} transactions failed to grade!")
    
    print(f"✅ Successfully graded {len(valid_grades)}/{len(transactions)} transactions")
    
    return valid_grades

def _grade_transaction(tx: Dict, location_id: str, step2_prompt: str, testing: bool) -> Dict:
    """Grade a single transaction"""
    transcript = (tx.get("meta") or {}).get("text","")
    tx_meta = tx.get("meta") or {}
    
    if not transcript.strip():
        # produce an empty row but keep columns
        base = map_step2_to_grade_cols({}, tx_meta)
        return {
            "transaction_id":  tx.get("id"),  # Add transaction ID
            "details":         base,
            "transcript":      transcript,
            "gpt_price":       0.0
        }

    # Run Step‑2 with location-specific menu data
    prompt = step2_prompt + "\n\nProcess this transcript:\n" + transcript
    try:
        if testing: 
            resp = client.responses.create(
                model=settings.STEP2_MODEL,
                include=["reasoning.encrypted_content"],
                input=[{"role":"user","content":[{"type":"input_text","text": prompt}]}],
                store=False,
                text={"format":{"type":"text"}},
                reasoning={"effort":"high","summary":"detailed"},
            )

        else: 
            resp = client.responses.create(
                model=settings.STEP2_MODEL,
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
        
        parsed = json_or_none(raw)
        if not parsed:
            parsed = {}
        print(f"Parsed JSON: {parsed}")

        gpt_price = calculate_gpt_price(resp)
    

    except Exception as ex:
        print(f"❌ Step‑2 error for transaction {tx.get('id', 'unknown')}: {ex}")
        print(f"   Transcript: {transcript[:100]}...")
        parsed = {}
        gpt_price = 0.0

    details = map_step2_to_grade_cols(parsed, tx.get("meta") or {})
    print(f"Mapped details: {details}")
    print("=" * 50)

    # Validate that we have a transaction ID
    transaction_id = tx.get("id")
    if not transaction_id:
        print(f"⚠️  WARNING: Transaction missing ID: {tx}")
        return None

    return {
        "transaction_id":  transaction_id,
        "details":         details,
        "transcript":      transcript,
        "gpt_price":       gpt_price
    }

# ---------- 3) GRADE (Step‑2 prompt per transaction, return ALL columns) ----------
def map_step2_to_grade_cols(step2_obj: Dict[str,Any], tx_meta: Dict[str,Any]) -> Dict[str,Any]:
    """Map numbered Step-2 keys (UPDATED) to `public.grades` columns with candidates + offered + converted."""
    print(f"Step2 object: {step2_obj}")
    print(f"Tx meta: {tx_meta}")

    out = {
        # Meta flags from tx, unchanged
        "complete_order":   ii(tx_meta.get("complete_order", 0)),
        "mobile_order":     ii(tx_meta.get("mobile_order", 0)),
        "coupon_used":      ii(tx_meta.get("coupon_used", 0)),
        "asked_more_time":  ii(tx_meta.get("asked_more_time", 0)),
        "out_of_stock_items": tx_meta.get("out_of_stock_items", "0"),

        # BEFORE items
        "items_initial":         step2_obj.get("1", "0"),
        "num_items_initial":     ii(step2_obj.get("2", 0)),

        # ---- Upsell (opportunities → offered → converted) ----
        "num_upsell_opportunities": ii(step2_obj.get("3", 0)),
        "upsell_main_items":        parse_json_field(step2_obj.get("4", "0")),
        "upsell_addon_items":       parse_json_field(step2_obj.get("5", "0")),
        "num_upsell_offers":        ii(step2_obj.get("6", 0)),
        "upsell_offered_main":      parse_json_field(step2_obj.get("7", "0")),
        "num_upsell_offered_main":  ii(step2_obj.get("6", 0)),
        "num_upsell_offered_addon": ii(step2_obj.get("8", 0)),
        "upsell_offered_addon":     parse_json_field(step2_obj.get("9", "0")),
        "num_upsell_success":       ii(step2_obj.get("10", 0)),
        "upsell_success_main":      parse_json_field(step2_obj.get("11", "0")),
        "num_upsell_success_addon": ii(step2_obj.get("12", 0)),
        "upsell_success_addon":     parse_json_field(step2_obj.get("13", "0")),

        # ---- Upsize (opportunities → offered → converted) ----
        "num_upsize_opportunities": ii(step2_obj.get("14", 0)),
        "upsize_items":             parse_json_field(step2_obj.get("15", "0")),
        "num_upsize_offers":        ii(step2_obj.get("16", 0)),
        "upsize_offered":           parse_json_field(step2_obj.get("17", "0")),
        "num_upsize_offered":       ii(step2_obj.get("16", 0)),
        "num_upsize_success":       ii(step2_obj.get("18", 0)),
        "upsize_success":           parse_json_field(step2_obj.get("19", "0")),

        # ---- Add-on (opportunities → offered → converted) ----
        "num_addon_opportunities":  ii(step2_obj.get("20", 0)),
        "addon_main_items":         parse_json_field(step2_obj.get("21", "0")),
        "addon_topping_items":      parse_json_field(step2_obj.get("22", "0")),
        "num_addon_offered_main":   ii(step2_obj.get("23", 0)),
        "addon_offered_main":       parse_json_field(step2_obj.get("24", "0")),
        "num_addon_offered_topping": ii(step2_obj.get("25", 0)),
        "addon_offered_topping":    parse_json_field(step2_obj.get("26", "0")),
        "num_addon_success_main":   ii(step2_obj.get("27", 0)),
        "addon_success_main":       parse_json_field(step2_obj.get("28", "0")),
        "num_addon_success_topping": ii(step2_obj.get("29", 0)),
        "addon_success_topping":    parse_json_field(step2_obj.get("30", "0")),

        # AFTER items
        "items_after":              step2_obj.get("31", "0"),
        "num_items_after":          ii(step2_obj.get("32", 0)),

        # Text feedback
        "feedback":                 step2_obj.get("33", ""),
        "issues":                   step2_obj.get("34", ""),

        # Optional extras
        "reasoning_summary":        step2_obj.get("reasoning_summary", "")
    }
    print(f"Out: {out}")
    return out


def build_step2_prompt(location_id: str) -> str:
    """Build the step 2 prompt with menu data from database or JSON fallback"""
    
    upselling, upsizing, addons, items, meals = get_menu_data_from_db(location_id)

    print(f"Menu data loaded: {len(upselling)} upselling scenarios, {len(upsizing)} upsizing scenarios, {len(addons)} add-ons, {len(items)} items, {len(meals)} meals")


    template = Prompts.template
    return (template
            .replace("<<UPSELLING_JSON>>", json.dumps(upselling))
            .replace("<<UPSIZING_JSON>>", json.dumps(upsizing))
            .replace("<<ADDONS_JSON>>", json.dumps(addons))
            .replace("<<ITEMS_JSON>>", json.dumps(items))
            .replace("<<MEALS_JSON>>", json.dumps(meals)))


def get_menu_data_from_db(location_id: str) -> tuple[list, list, list, list, list]:
    """Fetch menu data from database tables for the given location"""
    try:
        # Get items for this location
        items_result = db.get_items(location_id)
        
        # Get meals for this location
        meals_result = db.get_meals(location_id)
        
        # Get add-ons for this location
        addons_result = db.get_add_ons(location_id)
        
        # Convert to the format expected by the prompt
        items = []
        for item in items_result:
            items.append({
                "Item": item["item_name"],
                "Item ID": item["item_id"],
                "Size": item["size"],
                "Ordered Items Count": item["ordered_cnt"] or 1,
                "Upselling Chance": item["upsell"] or "0",
                "Upsizing Chance": item["upsize"] or "0",
                "Add on Chance": item["addon"] or "0"
            })
        
        meals = []
        for meal in meals_result:
            meals.append({
                "Item": meal["item_name"],
                "Item ID": meal["item_id"],
                "Ordered Items Count": meal["ordered_cnt"] or 1,
                "Inclusions": meal["inclusions"] or "",
                "Upselling Chance": meal["upsell"] or "0",
                "Upsizing Chance": meal["upsize"] or "0",
                "Add on Chance": meal["addon"] or "0"
            })
        
        addons = []
        for addon in addons_result:
            addons.append({
                "Item": addon["item_name"],
                "Item ID": addon["item_id"],
            })
        
        # For now, keep upselling and upsizing as static (can be moved to DB later if needed)
        upselling = read_json_or_empty(os.path.join(settings.PROMPTS_DIR, settings.UPSELLING_JSON))
        upsizing  = read_json_or_empty(os.path.join(settings.PROMPTS_DIR, settings.UPSIZING_JSON))
        
        print(f"Loaded menu data for location {location_id}: {len(items)} items, {len(meals)} meals, {len(addons)} add-ons")
        
        return upselling, upsizing, addons, items, meals
        
    except Exception as e:
        print(f"Error loading menu data from database: {e}")


def check_missing_grades(run_id: str) -> Dict[str, Any]:
    """Debug function to check for transactions without grades"""
    try:
        # Get all transactions for the run
        transactions_result = db.client.table("transactions").select("id, meta").eq("run_id", run_id).execute()
        all_transaction_ids = {tx["id"] for tx in transactions_result.data} if transactions_result.data else set()
        
        # Get all grades for the run
        grades_result = db.client.table("grades").select("transaction_id").execute()
        graded_transaction_ids = {grade["transaction_id"] for grade in grades_result.data} if grades_result.data else set()
        
        # Find missing grades
        missing_transaction_ids = all_transaction_ids - graded_transaction_ids
        
        print(f"🔍 Grade Check for Run {run_id}:")
        print(f"   Total transactions: {len(all_transaction_ids)}")
        print(f"   Graded transactions: {len(graded_transaction_ids)}")
        print(f"   Missing grades: {len(missing_transaction_ids)}")
        
        if missing_transaction_ids:
            print(f"   Missing transaction IDs: {list(missing_transaction_ids)}")
            
            # Get details of missing transactions
            missing_details = []
            for tx_id in missing_transaction_ids:
                tx_result = db.client.table("transactions").select("id, meta").eq("id", tx_id).single().execute()
                if tx_result.data:
                    transcript = (tx_result.data.get("meta") or {}).get("text", "")
                    missing_details.append({
                        "transaction_id": tx_id,
                        "has_transcript": bool(transcript.strip()),
                        "transcript_length": len(transcript),
                        "transcript_preview": transcript[:100] + "..." if len(transcript) > 100 else transcript
                    })
            
            print(f"   Missing transaction details: {missing_details}")
        
        return {
            "total_transactions": len(all_transaction_ids),
            "graded_transactions": len(graded_transaction_ids),
            "missing_grades": len(missing_transaction_ids),
            "missing_transaction_ids": list(missing_transaction_ids),
            "missing_details": missing_details if missing_transaction_ids else []
        }
        
    except Exception as e:
        print(f"Error checking missing grades: {e}")
        return {"error": str(e)}

