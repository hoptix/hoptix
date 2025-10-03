# grades transcations using openai 

from config import Prompts
import json
import os

def build_step2_prompt(db=None, location_id: str = None) -> str:
    """Build the step 2 prompt with menu data from database or JSON fallback"""
    
    upselling, upsizing, addons, items, meals = _get_menu_data_from_db(db, location_id)

    print(f"Menu data loaded: {len(upselling)} upselling scenarios, {len(upsizing)} upsizing scenarios, {len(addons)} add-ons, {len(items)} items, {len(meals)} meals")


    template = Prompts.template
    return (template
            .replace("<<UPSELLING_JSON>>", json.dumps(upselling))
            .replace("<<UPSIZING_JSON>>", json.dumps(upsizing))
            .replace("<<ADDONS_JSON>>", json.dumps(addons))
            .replace("<<ITEMS_JSON>>", json.dumps(items))
            .replace("<<MEALS_JSON>>", json.dumps(meals)))


# ---------- 3) GRADE (Step‑2 prompt per transaction, return ALL columns) ----------
def _map_step2_to_grade_cols(step2_obj: Dict[str,Any], tx_meta: Dict[str,Any]) -> Dict[str,Any]:
    """Map numbered Step-2 keys (UPDATED) to `public.grades` columns with candidates + offered + converted."""
    # Defaults
    def _ii(x, default=0):
        try:
            return int(x)
        except:
            return default

    # Parse JSON/JSONB-like fields
    def _parse_json_field(value, default="0"):
        if value is None:
            return default
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            s = value.strip()
            if s in ("", "0"):
                return default
            try:
                if s[0] in "{[":
                    import json
                    return json.loads(s)
                return value  # already a plain string like "0" or a CSV that upstream expects
            except:
                return value
        return value

    print(f"Step2 object: {step2_obj}")
    print(f"Tx meta: {tx_meta}")

    out = {
        # Meta flags from tx, unchanged
        "complete_order":   _ii(tx_meta.get("complete_order", 0)),
        "mobile_order":     _ii(tx_meta.get("mobile_order", 0)),
        "coupon_used":      _ii(tx_meta.get("coupon_used", 0)),
        "asked_more_time":  _ii(tx_meta.get("asked_more_time", 0)),
        "out_of_stock_items": tx_meta.get("out_of_stock_items", "0"),

        # BEFORE items
        "items_initial":         step2_obj.get("1", "0"),
        "num_items_initial":     _ii(step2_obj.get("2", 0)),

        # ---- Upsell (candidates → offered → converted) ----
        "num_upsell_opportunities": _ii(step2_obj.get("3", 0)),
        "upsell_base_items":        _parse_json_field(step2_obj.get("4_base", "0")),
        "upsell_candidate_items":   _parse_json_field(step2_obj.get("4", "0")),
        "num_upsell_offers":        _ii(step2_obj.get("5", 0)),
        "upsell_offered_items":     _parse_json_field(step2_obj.get("6", "0")),
        "upsell_success_items":     _parse_json_field(step2_obj.get("7", "0")),
        "num_upsell_success":       _ii(step2_obj.get("9", 0)),
        "num_largest_offers":       _ii(step2_obj.get("10", 0)),

        # ---- Upsize (candidates → offered → converted) ----
        "num_upsize_opportunities": _ii(step2_obj.get("11", 0)),
        "upsize_base_items":        _parse_json_field(step2_obj.get("11_base", "0")),
        "upsize_candidate_items":   _parse_json_field(step2_obj.get("12", "0")),
        "num_upsize_offers":        _ii(step2_obj.get("14", 0)),
        "upsize_offered_items":     _parse_json_field(step2_obj.get("14_offered", "0")),
        "upsize_success_items":     _parse_json_field(step2_obj.get("16", "0")),
        "num_upsize_success":       _ii(step2_obj.get("15", 0)),

        # ---- Add-on (candidates → offered → converted) ----
        "num_addon_opportunities":  _ii(step2_obj.get("18", 0)),
        "addon_base_items":         _parse_json_field(step2_obj.get("18_base", "0")),
        "addon_candidate_items":    _parse_json_field(step2_obj.get("19", "0")),
        "num_addon_offers":         _ii(step2_obj.get("21", 0)),
        "addon_offered_items":      _parse_json_field(step2_obj.get("21_offered", "0")),
        "addon_success_items":      _parse_json_field(step2_obj.get("23", "0")),
        "num_addon_success":        _ii(step2_obj.get("22", 0)),

        # AFTER items
        "items_after":              step2_obj.get("25", "0"),
        "num_items_after":          _ii(step2_obj.get("26", 0)),

        # Text feedback
        "feedback":                 step2_obj.get("27", ""),
        "issues":                   step2_obj.get("28", ""),

        # Optional extras
        "reasoning_summary":        step2_obj.get("reasoning_summary", "")
    }
    print(f"Out: {out}")
    return out



def _get_menu_data_from_db(db, location_id: str) -> tuple[list, list, list, list, list]:
    """Fetch menu data from database tables for the given location"""
    try:
        # Get items for this location
        items_result = db.client.table("items").select("*").eq("location_id", location_id).execute()
        
        # Get meals for this location
        meals_result = db.client.table("meals").select("*").eq("location_id", location_id).execute()
        
        # Get add-ons for this location
        addons_result = db.client.table("add_ons").select("*").eq("location_id", location_id).execute()
        
        # Convert to the format expected by the prompt
        items = []
        for item in items_result.data:
            items.append({
                "Item": item["item_name"],
                "Item ID": item["item_id"],
                "Size IDs": item["size_ids"],
                "Ordered Items Count": item["ordered_cnt"] or 1,
                "Upselling Chance": item["upsell"] or "0",
                "Upsizing Chance": item["upsize"] or "0",
                "Add on Chance": item["addon"] or "0"
            })
        
        meals = []
        for meal in meals_result.data:
            meals.append({
                "Item": meal["item_name"],
                "Item ID": meal["item_id"],
                "Size IDs": meal["size_ids"],
                "Ordered Items Count": meal["ordered_cnt"] or 1,
                "Inclusions": meal["inclusions"] or "",
                "Upselling Chance": meal["upsell"] or "0",
                "Upsizing Chance": meal["upsize"] or "0",
                "Add on Chance": meal["addon"] or "0"
            })
        
        addons = []
        for addon in addons_result.data:
            addons.append({
                "Item": addon["item_name"],
                "Item ID": addon["item_id"],
                "Size IDs": addon["size_ids"]
            })
        
        # For now, keep upselling and upsizing as static (can be moved to DB later if needed)
        upselling = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.UPSELLING_JSON))
        upsizing  = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.UPSIZING_JSON))
        
        print(f"Loaded menu data for location {location_id}: {len(items)} items, {len(meals)} meals, {len(addons)} add-ons")
        
        return upselling, upsizing, addons, items, meals
        
    except Exception as e:
        print(f"Error loading menu data from database: {e}")