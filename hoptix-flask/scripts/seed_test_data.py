import os, uuid, datetime as dt
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

S3_PREFIX = os.getenv("S3_PREFIX", "dev/sample")   # change if needed
DURATION_SEC = int(os.getenv("SEED_VIDEO_DURATION_SEC", "10"))

def upsert_one(table, row, keys):
    q = client.table(table).upsert(row, on_conflict=",".join(keys)).execute()
    return q.data[0] if q.data else row

# IDs for a single run
org_id = str(uuid.uuid4())
loc_id = str(uuid.uuid4())
run_id = str(uuid.uuid4())

# 1) org
upsert_one("orgs", {"id": org_id, "name": "Test Org"}, ["id"])

# 2) location
upsert_one("locations", {
    "id": loc_id,
    "org_id": org_id,
    "name": "Test Location",
    "tz": "America/New_York"
}, ["id"])

# 3) run (today)
today = dt.date.today().isoformat()
upsert_one("runs", {
    "id": run_id,
    "org_id": org_id,
    "location_id": loc_id,
    "run_date": today,
    "status": "uploaded"
}, ["id"])

# 4) videos in the folder: sample, sample1, ..., sample4
#    We’ll stagger started_at by +15s each, just to differentiate.
base_start = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
video_names = ["DT_File20250817120001000"]

created_ids = []
for i, name in enumerate(video_names):
    started_at = base_start + dt.timedelta(seconds=15 * i)
    ended_at   = started_at + dt.timedelta(seconds=DURATION_SEC)
    s3_key     = f"{S3_PREFIX}/{name}.avi"

    video_id = str(uuid.uuid4())
    upsert_one("videos", {
        "id": video_id,
        "run_id": run_id,
        "location_id": loc_id,
        "camera_id": f"test-cam-{i+1}",
        "s3_key": s3_key,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "status": "uploaded",
        "meta": {}
    }, ["id"])
    created_ids.append((video_id, s3_key))

print("OK seeded:")
print("org_id   :", org_id)
print("loc_id   :", loc_id)
print("run_id   :", run_id)
for vid, key in created_ids:
    print(f"video_id : {vid}   s3_key: {key}")

print("\nNext:")
print(" - Make sure these objects exist in S3 at the same keys shown above.")
print(" - Run: `python -m worker.runner` (continuous) or `python -m worker.run_once` (single job).")