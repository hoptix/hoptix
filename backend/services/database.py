# supabase client 
from supabase import create_client, Client
from typing import Any, Optional
from config import Settings
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

    def set_audio_status(self, audio_id: str, status: str):
        self.client.table("audios").update({"status": status}).eq("id", audio_id).execute()

    def set_audio_to_processing(self, audio_id: str):
            self.client.table("audios").update({"status": "processing"}).eq("id", audio_id).execute()

    def set_audio_link(self, audio_id: str, gdrive_path: str):
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

    def create_audio(self, location_id: str, date: str, gdrive_path: str, started_at="10:00:00", ended_at="22:00:00"):
        # Convert time-only strings into full ISO 8601 timestamps for timestamptz columns
        started_at_ts = f"{date}T{started_at}Z"
        ended_at_ts = f"{date}T{ended_at}Z"
        
        res = self.client.table("audios").insert({
            "location_id": location_id,
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
    
    def get_items(self):
        """Get all menu items"""
        result = self.client.table("items").select("*").execute()
        return result.data if result.data else []
    
    def insert_analytics(self, analytics: dict):
        """Insert analytics into database"""
        self.client.table("analytics").insert(analytics).execute()

    def upsert_grades(self, grades: list[dict]):
        """Upsert grades into database"""
        self.client.table("grades").upsert(grades, on_conflict="transaction_id").execute()

    def upsert_transactions(self, transactions: list[dict]):
        """Insert transactions into database"""
        if not transactions:
            return

        self.client.table("transactions").upsert(transactions).execute()