import json
import os
from typing import Dict, Any
from services.database import Supa
from services.items import ItemLookupService
import logging
import psutil
from datetime import datetime, timedelta
from dateutil import parser as dateparse

logger = logging.getLogger(__name__)

db = Supa()

def iso_from_start(base_iso: str, seconds_from_start: float) -> str:
    return (dateparse.isoparse(base_iso) + timedelta(seconds=float(seconds_from_start))).isoformat()


def iso_or_die(value: str) -> str:
    dt = dateparse.isoparse(value)
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone offset")
    return dt.isoformat()

def parse_json_field(value, default="0"):
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


# Helper function for safe integer conversion
def ii(x, default=0): 
    try: return int(x)
    except: return default


def json_or_none(txt: str) -> Dict[str, Any] | None:
    try:
        return json.loads(txt.strip())
    except Exception:
        return None

def read_json_or_empty(path: str) -> list | dict:
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def calculate_gpt_price(resp: Any) -> float:
    if hasattr(resp, 'usage'):
        input_cost = (resp.usage.input_tokens / 1000000) * 2.0
        output_cost = (resp.usage.output_tokens / 1000000) * 8.0
        return input_cost + output_cost
    return 0.0

def calculate_gpt_price_batch(resp: Any) -> float:
    if hasattr(resp, 'usage'):
        input_cost = (resp.usage.input_tokens / 1000000) * 1.0
        output_cost = (resp.usage.output_tokens / 1000000) * 4.0
        return input_cost + output_cost
    return 0.0


def convert_item_ids_to_names(item_data, item_lookup: ItemLookupService) -> str:
    """Convert item IDs to human-readable names. Handles strings, lists, numbers, and None."""
    if not item_data or item_data in ['0', '[]', 'None', 'null', None, 0]:
        return 'None'
    
    try:
        # Handle different data types
        if isinstance(item_data, list):
            item_list = item_data
        elif isinstance(item_data, (int, float)):
            # Single numeric item ID
            item_list = [str(item_data)]
        elif isinstance(item_data, str):
            if item_data.startswith('[') and item_data.endswith(']'):
                # Parse as proper JSON array
                item_list = json.loads(item_data)
            else:
                # Single item or comma-separated
                item_list = [item_data.strip()]
        else:
            item_list = [str(item_data)]
        
        # Convert each item ID to name
        item_names = []
        for item_id in item_list:
            if item_id and str(item_id) != '0' and str(item_id).strip():
                item_name = item_lookup.get_item_name(str(item_id).strip())
                item_names.append(item_name)
        
        return ', '.join(item_names) if item_names else 'None'
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"Failed to convert item data '{item_data}': {e}")
        return str(item_data)  # Return original if parsing fails



def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def log_memory_usage(step_name: str, step_number: int, total_steps: int):
    """Log memory usage for a pipeline step"""
    memory_mb = get_memory_usage()
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{step_number}/{total_steps}] {step_name} - Memory: {memory_mb:.1f} MB")