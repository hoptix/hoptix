"""
Later, import your existing functions and write results back to Supabase using db.client.
"""

from integrations.db_supabase import Supa
from worker.pipeline import main_loop

def fetch_one_uploaded_video(db: Supa):
    res = db.client.table("videos").select("id, s3_key, run_id").eq("status", "uploaded").limit(1).execute()
    if res.data:
        v = res.data[0]
        return v["id"], v["s3_key"], v["run_id"]
    return None

def mark_status(db: Supa, video_id: str, status: str):
    db.client.table("videos").update({"status": status}).eq("id", video_id).execute()

if __name__ == "__main__":
    main_loop()