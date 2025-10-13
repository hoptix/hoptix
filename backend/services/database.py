# supabase client 
from supabase import create_client, Client
from typing import Any, Optional
from config import Settings
from datetime import datetime, timedelta

class Supa:

    def __init__(self):
        self.client: Client = create_client(Settings.SUPABASE_URL, Settings.SUPABASE_SERVICE_KEY)

    # ------- runs -------
    def insert_run(self, location_id: str, run_date: str) -> str:
        org_id = self.client.table("locations").select("org_id").eq("id", location_id).limit(1).execute().data[0]["org_id"]

        res = self.client.table("runs").insert({
            "org_id": org_id,
            "location_id": location_id,
            "run_date": run_date,
            "status": "uploading"
        }).execute()
        return res.data[0]["id"]

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        res = self.client.table("runs").select(
            "id, org_id, location_id, run_date, status"
        ).eq("id", run_id).single().execute()
        return res.data if res.data else None

    # ------- videos -------
    def insert_video(self, run_id: str, location_id: str, camera_id: str,
                     key: str, started_at: str, ended_at: str) -> str:
        res = self.client.table("videos").insert({
            "run_id": run_id,
            "location_id": location_id,
            "camera_id": camera_id,
            "s3_key": key,
            "started_at": started_at,
            "ended_at": ended_at,
            "status": "uploading"
        }).execute()
        return res.data[0]["id"]

    def get_videos_from_location_and_date(self, location_id: str, date: str):
        res = self.client.table("videos").select("*").eq("location_id", location_id).eq("date", date).execute()
        return res.data, res.status

    def get_video_key(self, video_id: str, run_id: str) -> Optional[str]:
        res = self.client.table("videos").select("s3_key").eq("id", video_id).eq("run_id", run_id).single().execute()
        return res.data["s3_key"] if res.data else None

    def mark_video_uploaded(self, video_id: str):
        self.client.table("videos").update({"status": "uploaded"}).eq("id", video_id).execute()

    def get_audio_from_location_and_date(self, location_id: str, date: str):
        res = self.client.table("audios").select("*").eq("location_id", location_id).eq("date", date).execute()

        if len(res.data) == 0:
            return None, None
        
        return res.data[0]["id"], res.data[0]["status"]

    def get_location_name(self, location_id: str):
        res = self.client.table("locations").select("name").eq("id", location_id).execute()
        return res.data[0]["name"]

    def get_org_name(self, location_id: str):
        """Get organization name from location_id"""
        # First get org_id from location
        location_res = self.client.table("locations").select("org_id").eq("id", location_id).execute()
        if not location_res.data:
            return "Unknown Org"

        org_id = location_res.data[0]["org_id"]

        # Then get org name from orgs table
        org_res = self.client.table("orgs").select("name").eq("id", org_id).execute()
        if not org_res.data:
            return "Unknown Org"

        return org_res.data[0]["name"]

    def get_org_name_by_id(self, org_id: str):
        """Get organization name from org_id directly"""
        org_res = self.client.table("orgs").select("name").eq("id", org_id).execute()
        if not org_res.data:
            return "Unknown Org"
        return org_res.data[0]["name"]

    def set_audio_status(self, audio_id: str, status: str):
        self.client.table("audios").update({"status": status}).eq("id", audio_id).execute()

    def set_audio_to_processing(self, audio_id: str):
            self.client.table("audios").update({"status": "processing"}).eq("id", audio_id).execute()

    def set_audio_link(self, audio_id: str, gdrive_path: str):
        """Safely set the audio link, avoiding unique-constraint violations.

        If another row already has this link, we do not overwrite and simply keep
        the existing value to avoid 23505 conflicts.
        """
        # If this exact link already exists on some row, avoid violating unique constraint
        existing = self.client.table("audios").select("id").eq("link", gdrive_path).limit(1).execute()
        if existing.data and existing.data[0]["id"] != audio_id:
            # Another record already owns this link; skip update for this audio_id
            return
        self.client.table("audios").update({"link": gdrive_path}).eq("id", audio_id).execute()

    def set_pipeline_to_complete(self, run_id: str, audio_id: str):

        #set run status to complete
        self.client.table("runs").update({"status": "complete"}).eq("id", run_id).execute()

        #set audio status to ready 
        self.client.table("audios").update({"status": "ready"}).eq("id", audio_id).execute()
    
    def audio_exists(self, location_id: str, date: str):
        res = self.client.table("audios").select("id").eq("location_id", location_id).eq("date", date).execute()
        return len(res.data) > 0

    def get_audio_id(self, location_id: str, date: str):
        res = self.client.table("audios").select("id").eq("location_id", location_id).eq("date", date).execute()
        return res.data[0]["id"]

    def create_audio(self, location_id: str, run_id: str, date: str, gdrive_path: str, started_at="10:00:00", ended_at="22:00:00"):
        # Convert time-only strings into full ISO 8601 timestamps for timestamptz columns
        started_at_ts = f"{date}T{started_at}Z"
        ended_at_ts = f"{date}T{ended_at}Z"
        
        # If a record already exists with this link, return it instead of inserting
        existing_link = self.client.table("audios").select("id").eq("link", gdrive_path).limit(1).execute()
        if existing_link.data:
            return existing_link.data[0]["id"]

        res = self.client.table("audios").insert({
            "location_id": location_id,
            "run_id": run_id,
            "date": date,
            "started_at": started_at_ts,
            "ended_at": ended_at_ts,
            "link": gdrive_path,
            "status": "uploaded"
        }).execute()
        return res.data[0]["id"]

    def set_audio_to_ready(self, audio_id: str):
        self.client.table("audios").update({"status": "ready"}).eq("id", audio_id).execute()

    def set_audio_to_processing(self, audio_id: str):
        self.client.table("audios").update({"status": "processing"}).eq("id", audio_id).execute()
    
    def view(self, view_name: str):
        """Access database views"""
        return self.client.table(view_name)
    
    def get_items(self, location_id: str):
        """Get all menu items"""
        result = self.client.table("items").select("*").eq("location_id", location_id).execute()
        return result.data if result.data else []
    
    def insert_analytics(self, analytics: dict):
        """Insert analytics into database"""
        self.client.table("analytics").insert(analytics).execute()

    def upsert_grades(self, grades: list[dict]):
        """Upsert grades into database"""
        self.client.table("grades").upsert(grades, on_conflict="transaction_id").execute()
        if not grades:
            return
        
        # Flatten the nested structure
        flattened_grades = []
        for grade in grades:
            flattened = {
                "transaction_id": grade.get("transaction_id"),
                "transcript": grade.get("transcript"),
                "gpt_price": grade.get("gpt_price"),
                **grade.get("details", {})  # Spread the details into the main object
            }
            flattened_grades.append(flattened)
        
        self.client.table("grades").upsert(flattened_grades, on_conflict="transaction_id").execute()
    
    def get_audio_record(self, audio_id: str) -> Optional[dict]:
        """Get audio record by ID"""
        res = self.client.table("audios").select("*").eq("id", audio_id).single().execute()
        return res.data if res.data else None
    
    def get_audio_records_by_run_id(self, run_id: str) -> list[dict]:
        """Get all audio records for a run (including chunks)"""
        res = self.client.table("audios").select("*").eq("run_id", run_id).execute()
        return res.data if res.data else []

    def upsert_transactions(self, transactions: list[dict]):
        """Insert transactions into database and return them with IDs"""
        if not transactions:
            return []

        result = self.client.table("transactions").upsert(transactions).execute()
        print(f"Inserted {len(result.data)} transactions")
        print(f"Transactions: {result.data}")
        return result.data

    def get_meals(self, location_id: str):
        result = self.client.table("meals").select("*").eq("location_id", location_id).execute()
        return result.data if result.data else []

    def get_transactions(self, run_id: str, limit: int = 0):
        """Get transactions for a run"""
        query = self.client.table("transactions").select("*").eq("run_id", run_id)
        if limit > 0:
            query = query.limit(limit)
        result = query.execute()
        return result.data if result.data else []

    def update_transaction(self, transaction_id: str, updates: dict):
        """Update a transaction record"""
        self.client.table("transactions").update(updates).eq("id", transaction_id).execute()

    def get_add_ons(self, location_id: str):
        result = self.client.table("add_ons").select("*").eq("location_id", location_id).execute()
        return result.data if result.data else []

    def get_location_from_run(self, run_id: str):
        result = self.client.table("runs").select("location_id").eq("id", run_id).execute()
        return result.data[0]["location_id"]

    def get_items_prices(self, location_id: str):
        """Get item prices as a dict mapping item_id_size to price"""
        result = self.client.table("items").select("item_id, size_ids, price").eq("location_id", location_id).execute()
        prices = {}
        print(f"🔍 DEBUG: get_items_prices for location {location_id}: {len(result.data)} items found")
        for item in result.data:
            if item.get("size_ids"):
                for size_id in item["size_ids"]:
                    key = f"{item['item_id']}_{size_id}"
                    price = float(item["price"]) if item.get("price") else 0.0
                    prices[key] = price
                    print(f"🔍 DEBUG: Item {key} has price {price}")
            else:
                print(f"🔍 DEBUG: Item {item['item_id']} has no size_ids")
        print(f"🔍 DEBUG: Total items prices: {len(prices)}")
        return prices

    def get_meals_prices(self, location_id: str):
        """Get meal prices as a dict mapping item_id_size to price"""
        result = self.client.table("meals").select("item_id, size_ids, price").eq("location_id", location_id).execute()
        prices = {}
        print(f"🔍 DEBUG: get_meals_prices for location {location_id}: {len(result.data)} meals found")
        for meal in result.data:
            if meal.get("size_ids"):
                for size_id in meal["size_ids"]:
                    key = f"{meal['item_id']}_{size_id}"
                    price = float(meal["price"]) if meal.get("price") else 0.0
                    prices[key] = price
                    print(f"🔍 DEBUG: Meal {key} has price {price}")
            else:
                print(f"🔍 DEBUG: Meal {meal['item_id']} has no size_ids")
        print(f"🔍 DEBUG: Total meals prices: {len(prices)}")
        return prices

    def get_addons_prices(self, location_id: str):
        """Get addon prices as a dict mapping item_id to price"""
        result = self.client.table("add_ons").select("item_id, price").eq("location_id", location_id).execute()
        prices = {}
        print(f"🔍 DEBUG: get_addons_prices for location {location_id}: {len(result.data)} addons found")
        for item in result.data:
            item_id = str(item["item_id"])
            price = float(item["price"]) if item.get("price") else 0.0
            prices[item_id] = price
            print(f"🔍 DEBUG: Addon {item_id} has price {price}")
        print(f"🔍 DEBUG: Total addon prices: {len(prices)}")
        return prices

    def get_operator_feedback_raw(self, operator_id: str, run_id: str = None, days: int = 30, limit: int = 50) -> list[dict]:
        """Get operator feedback from the database"""
        time_filter = (datetime.now() - timedelta(days=days)).isoformat()

        if run_id and operator_id:
            result = self.client.table("graded_rows_filtered").select("transaction_id, feedback").eq("worker_id", operator_id).eq("run_id", run_id).gte("begin_time", time_filter).limit(limit).execute()
            return result.data if result.data else []

        elif operator_id:
            result = self.client.table("graded_rows_filtered").select("transaction_id, feedback").eq("worker_id", operator_id).gte("begin_time", time_filter).limit(limit).execute()
            return result.data if result.data else []

        elif run_id:
            result = self.client.table("graded_rows_filtered").select("transaction_id, feedback").eq("run_id", run_id).gte("begin_time", time_filter).limit(limit).execute()
            return result.data if result.data else []

        return []

    def insert_operator_feedback(self, operator_id: str, feedback: str):
        """Insert operator feedback into the database"""
        self.client.table("workers").update({
            "monthly_feedback": feedback
        }).eq("id", operator_id).execute()
    
    def get_operator_monthly_feedback(self, operator_id: str):
        """Get operator monthly feedback from the database"""
        result = self.client.table("workers").select("monthly_feedback").eq("id", operator_id).execute()
        return result.data[0]["monthly_feedback"] if result.data else None