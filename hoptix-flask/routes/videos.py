import math, datetime as dt
from flask import Blueprint, current_app, request
from integrations.s3_client import get_s3, create_multipart, presign_parts, complete_multipart

videos_bp = Blueprint("videos", __name__)

def mint_key(org_id: str, location_id: str, run_id: str, camera_id: str, started_at_iso: str):
    d = dt.datetime.fromisoformat(started_at_iso.replace("Z","+00:00")).date()
    return f"org={org_id}/loc={location_id}/date={d.year:04d}/{d.month:02d}/{d.day:02d}/run={run_id}/cam={camera_id}/input.mp4"

@videos_bp.post("/initiate")
def initiate(run_id):
    s = current_app.config["SETTINGS"]
    db = current_app.config["DB"]
    body = request.get_json(force=True)

    camera_id  = body["camera_id"]
    started_at = body["started_at"]  # ISO8601 UTC
    ended_at   = body["ended_at"]
    size_bytes = int(body["size_bytes"])
    content_type = body.get("content_type","video/mp4")

    run = db.get_run(run_id)
    if not run: return {"error":"run not found"}, 404

    key = mint_key(run["org_id"], run["location_id"], run_id, camera_id, started_at)
    video_id = db.insert_video(run_id, run["location_id"], camera_id, key, started_at, ended_at)

    s3 = get_s3(s.AWS_REGION)
    upload_id = create_multipart(s3, s.RAW_BUCKET, key, content_type)
    part_size = s.PART_SIZE_BYTES
    part_count = max(1, math.ceil(size_bytes / part_size))
    urls = presign_parts(s3, s.RAW_BUCKET, key, upload_id, range(1, part_count+1), s.URL_TTL_SECONDS)

    return {
        "video_id": video_id,
        "s3_key": key,
        "uploadId": upload_id,
        "partSize": part_size,
        "urls": urls
    }, 200

@videos_bp.post("/complete")
def complete(run_id):
    s = current_app.config["SETTINGS"]
    db = current_app.config["DB"]
    body = request.get_json(force=True)

    video_id = body["video_id"]
    upload_id = body["uploadId"]
    parts = sorted(body["parts"], key=lambda p: p["PartNumber"])

    run = db.get_run(run_id)
    if not run: return {"error":"run not found"}, 404

    key = db.get_video_key(video_id, run_id)
    if not key: return {"error":"video not found"}, 404

    s3 = get_s3(s.AWS_REGION)
    complete_multipart(s3, s.RAW_BUCKET, key, upload_id, parts)
    db.mark_video_uploaded(video_id)
    return {"ok": True}, 200