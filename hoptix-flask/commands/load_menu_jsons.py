#!/usr/bin/env python3
"""Bulk-load local menu JSON files into Supabase tables.
Reads items.json, meals.json, misc_items.json, store_map.json from prompts/ and
upserts each record into its corresponding table (dq_items, dq_meals,
dq_misc_items, dq_stores).

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY env vars.
"""
import json, os, pathlib, sys
from dotenv import load_dotenv
from supabase import create_client
from typing import Dict, List

load_dotenv(dotenv_path=pathlib.Path(__file__).resolve().parent.parent / ".env")

SUPA_URL  = os.getenv("SUPABASE_URL")
SERVICE_K = os.getenv("SUPABASE_SERVICE_KEY")
if not SUPA_URL or not SERVICE_K:
    sys.exit("❌ SUPABASE_URL or SUPABASE_SERVICE_KEY not set in env")

sb = create_client(SUPA_URL, SERVICE_K)

BASE = pathlib.Path(__file__).resolve().parent.parent / "prompts"
FILES = {
    "items": BASE / "items.json",
    "meals": BASE / "meals.json",
    "misc_items": BASE / "misc_items.json",
    "store_map": BASE / "store_map.json",
}

TABLE_MAP = {
    "items": {
        "table": "items",
        "pk": "item_id",
        "load": lambda r: {
            "item_id": r["Item ID"],
            "item_name": r["Item"],
            "ordered_cnt": r["Ordered Items Count"],
            "size_ids": r["Size IDs"],
            "upsell": r["Upselling Chance"],
            "upsize": r["Upsizing Chance"],
            "addon": r["Add on Chance"],
            "store_ids": r["Store IDs"],
        },
    },
    "meals": {
        "table": "meals",
        "pk": "item_id",
        "load": lambda r: {
            "item_id": r["Item ID"],
            "item_name": r["Item"],
            "ordered_cnt": r["Ordered Items Count"],
            "inclusions": r["Order Inclusions for Combo/Meal"],
            "upsell": r["Upselling Chance"],
            "upsize": r["Upsizing Chance"],
            "addon": r["Add on Chance"],
            "size_ids": r["Size IDs"],
            "store_ids": r["Store IDs"],
        },
    },
    "misc_items": {
        "table": "misc_items",
        "pk": "item_id",
        "load": lambda r: {
            "item_id": r["Item ID"],
            "item_name": r["Item"],
            "size_ids": r["Size IDs"],
            "store_ids": r["Store IDs"],
        },
    },
    "store_map": {
        "table": "stores",
        "pk": "store_id",
        "load": lambda kv: {"store_id": int(kv[0]), "store_name": kv[1]},
    },
}

def upsert(table: str, rows: List[Dict], pk: str):
    CHUNK = 500
    for i in range(0, len(rows), CHUNK):
        sb.table(table).upsert(rows[i:i+CHUNK], on_conflict=pk).execute()
    print(f"✔ {len(rows)} rows → {table}")

def main():
    for key, path in FILES.items():
        meta = TABLE_MAP[key]
        if key == "store_map":
            data = json.load(open(path, "r", encoding="utf-8"))
            rows = [meta["load"](kv) for kv in data.items()]
        else:
            data = json.load(open(path, "r", encoding="utf-8"))
            rows = [meta["load"](r) for r in data]
        upsert(meta["table"], rows, meta["pk"])

if __name__ == "__main__":
    main()
