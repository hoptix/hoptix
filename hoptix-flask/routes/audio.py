import math, datetime as dt, mimetypes
from flask import Blueprint, current_app, request
from integrations.s3_client import (
    get_s3, create_multipart, presign_parts, complete_multipart, abort_multipart
)

audio_bp = Blueprint("audio", __name__)

def _ext_from_filename_or_ct(filename: str | None, content_type: str | None) -> str:
    if filename and "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    if content_type:
        ext = mimetypes.guess_extension(content_type)  # returns like ".mp3"
        if ext and len(ext) > 1:
            return ext[1:]
    return "mp3"  # default

def mint_key(org_id: str, location_id: str, run_id: str, station_id: str, started_at_iso: str, ext: str):
    d = dt.datetime.fromisoformat(started_at_iso.replace("Z","+00:00")).date()
    # Keep your partition layout; name file "input.<ext>"
    return (
        f"org={org_id}/loc={location_id}/date={d.year:04d}/{d.month:02d}/{d.day:02d}/"
        f"run={run_id}/station={station_id}/input.{ext}"
    )

@audio_bp.post("/audio/<run_id>/initiate")
def initiate(run_id):
    s = current_app.config["SETTINGS"]
    db = current_app.config["DB"]
    body = request.get_json(force=True)

    # required body fields
    station_id   = body["station_id"]          # was camera_id; rename on FE
    started_at   = body["started_at"]          # ISO8601 UTC
    ended_at     = body["ended_at"]            # ISO8601 UTC
    size_bytes   = int(body["size_bytes"])
    filename     = body.get("filename")        # optional, helps select extension
    content_type = body.get("content_type","audio/mpeg")

    run = db.get_run(run_id)
    if not run:
        return {"error":"run not found"}, 404

    ext = _ext_from_filename_or_ct(filename, content_type)
    key = mint_key(run["org_id"], run["location_id"], run_id, station_id, started_at, ext)

    # still using videos table for the single audio blob (minimal change)
    audio_id = db.insert_video(run_id, run["location_id"], station_id, key, started_at, ended_at)

    s3 = get_s3(s.AWS_REGION)
    upload_id = create_multipart(s3, s.RAW_BUCKET, key, content_type)
    part_size = s.PART_SIZE_BYTES
    part_count = max(1, math.ceil(size_bytes / part_size))
    urls = presign_parts(s3, s.RAW_BUCKET, key, upload_id, range(1, part_count+1), s.URL_TTL_SECONDS)

    return {
        "video_id": audio_id,         # keep field name to match your worker
        "s3_key": key,
        "uploadId": upload_id,
        "partSize": part_size,
        "urls": urls
    }, 200

@audio_bp.post("/audio/<run_id>/complete")
def complete(run_id):
    s = current_app.config["SETTINGS"]
    db = current_app.config["DB"]
    body = request.get_json(force=True)

    video_id  = body["video_id"]  # id returned from initiate
    upload_id = body["uploadId"]
    parts     = sorted(body["parts"], key=lambda p: p["PartNumber"])

    run = db.get_run(run_id)
    if not run:
        return {"error":"run not found"}, 404

    key = db.get_video_key(video_id, run_id)
    if not key:
        return {"error":"audio not found"}, 404

    s3 = get_s3(s.AWS_REGION)
    complete_multipart(s3, s.RAW_BUCKET, key, upload_id, parts)

    # mark uploaded so worker can pick it up
    db.mark_video_uploaded(video_id)

    # (optional) enqueue SQS message here if you push instead of poll
    # current_app.config["QUEUE"].send_video_uploaded(run_id, video_id, key)

    return {"ok": True}, 200

@audio_bp.post("/audio/<run_id>/abort")
def abort(run_id):
    """Optional: let client cancel an in-progress multipart upload."""
    s = current_app.config["SETTINGS"]
    db = current_app.config["DB"]
    body = request.get_json(force=True)

    video_id  = body["video_id"]
    upload_id = body["uploadId"]

    run = db.get_run(run_id)
    if not run:
        return {"error":"run not found"}, 404

    key = db.get_video_key(video_id, run_id)
    if not key:
        return {"error":"audio not found"}, 404

    s3 = get_s3(s.AWS_REGION)
    abort_multipart(s3, s.RAW_BUCKET, key, upload_id)

    # reflect status if you like:
    db.mark_video_failed(video_id)

    return {"ok": True}, 200