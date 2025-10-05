import json
import os
from typing import Dict, Any


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