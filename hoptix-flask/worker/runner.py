"""
Later, import your existing functions and write results back to Supabase using db.client.
"""
import time
from config import Settings
from integrations.db_supabase import Supa

def fetch_one_uploaded_video(db: Supa):
    res = db.client.table("videos").select("id, s3_key, run_id").eq("status", "uploaded").limit(1).execute()
    if res.data:
        v = res.data[0]
        return v["id"], v["s3_key"], v["run_id"]
    return None

def mark_status(db: Supa, video_id: str, status: str):
    db.client.table("videos").update({"status": status}).eq("id", video_id).execute()

def process_video(db: Supa, video_id: str, s3_key: str):
    # TODO:
    # 1) download from RAW_BUCKET/key to /tmp/video.mp4
    # 2) call your existing splitter/transcriber/grader
    # 3) insert into 'transactions' and 'grades' via db.client.table(...).insert(...)
    pass

if __name__ == "__main__":
    s = Settings()
    db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)

    while True:
        row = fetch_one_uploaded_video(db)
        if not row:
            time.sleep(5); continue
        video_id, key, run_id = row
        try:
            mark_status(db, video_id, "processing")
            process_video(db, video_id, key)
            mark_status(db, video_id, "ready")
        except Exception as e:
            print("worker error:", e)
            time.sleep(2)