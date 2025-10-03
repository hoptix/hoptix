# supabase client 
from supabase import create_client, Client
from typing import Any, Optional

class Supa:
    def __init__(self, url: str, service_key: str):
        self.client: Client = create_client(url, service_key)

    # ------- runs -------
    def insert_run(self, org_id: str, location_id: str, run_date: str) -> str:
        res = self.client.table("runs").insert({
            "org_id": org_id,
            "location_id": location_id,
            "run_date": run_date,
            "status": "uploading"
        }).select("id").single().execute()
        return res.data["id"]

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
        }).select("id").single().execute()
        return res.data["id"]

    def get_videos_from_location_and_date(self, location_id: str, date: str):
        res = self.client.table("videos").select("*").eq("location_id", location_id).eq("date", date).execute()
        return res.data, res.status

    def get_video_key(self, video_id: str, run_id: str) -> Optional[str]:
        res = self.client.table("videos").select("s3_key").eq("id", video_id).eq("run_id", run_id).single().execute()
        return res.data["s3_key"] if res.data else None

    def mark_video_uploaded(self, video_id: str):
        self.client.table("videos").update({"status": "uploaded"}).eq("id", video_id).execute()