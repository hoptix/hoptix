#!/usr/bin/env python3
"""
Cut audio clips from a long WAV based on Supabase transactions,
upload the main WAV to Google Drive, and upload individual clips with links to transactions.

- Downloads WAV from ~/Downloads folder
- Uploads main WAV to Google Drive
- Computes recording T0 from anchor mapping
- For each transaction: start_sec = (started_at - T0), end_sec = (ended_at - T0)
- Cuts with ffmpeg into individual .wav clips
- Uploads clips to Google Drive and updates transaction records

Usage:
  export SUPABASE_URL="https://<your-project>.supabase.co"
  export SUPABASE_KEY="service_role_or_anon_key"

  python cut_tx_audio_supabase.py \
      --wav-filename "long_audio.wav" \
      --anchor-started-at "2025-10-01T10:29:27.559790+00:00" \
      --anchor-wav "03:45:57" \
      --run-id UUID \
      [--limit 0]
"""

import argparse
import os
import subprocess
import uuid
import wave
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
import dotenv

from dateutil import parser as dtparser
from supabase import create_client, Client
from integrations.gdrive_client import GoogleDriveClient

dotenv.load_dotenv()


def ffprobe_duration_seconds(wav_path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        wav_path
    ])
    return float(out.decode().strip())


def get_wav_duration_seconds(wav_path: str) -> float:
    # Try stdlib wave for PCM; fall back to ffprobe for anything else.
    try:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
        return frames / float(rate)
    except wave.Error:
        return ffprobe_duration_seconds(wav_path)


def iso_or_die(value: str) -> datetime:
    dt = dtparser.isoparse(value)
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone offset")
    return dt


def parse_hms(s: str) -> int:
    parts = s.split(":")
    if len(parts) != 3:
        raise ValueError("--anchor-wav must be HH:MM:SS (e.g., 03:45:57)")
    h, m, sec = parts
    return int(h) * 3600 + int(m) * 60 + int(sec)


def ffmpeg_cut(wav_path: str, out_path: str, start_sec: float, end_sec: float) -> None:
    duration = max(0.0, end_sec - start_sec)
    if duration <= 0.0:
        return
    cmd = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-ss", f"{start_sec:.3f}",
        "-i", wav_path,
        "-t", f"{duration:.3f}",
        "-c", "copy",  # fast for WAV; switch to "pcm_s16le" if copy fails for your file
        out_path,
    ]
    subprocess.run(cmd, check=True)


def upload_to_gdrive_and_get_link(local_path: str, folder_name: str, filename: str) -> str:
    """Upload file to Google Drive and return shareable link"""
    try:
        gdrive = GoogleDriveClient()
        file_id = gdrive.upload_file(local_path, folder_name, filename)
        if file_id:
            return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        return None
    except Exception as e:
        print(f"❌ Error uploading to Google Drive: {e}")
        return None

def get_downloads_path():
    """Get the Downloads folder path"""
    home = os.path.expanduser("~")
    downloads = os.path.join(home, "Downloads")
    return downloads

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav-filename", required=True, help="Filename of the WAV file in Downloads folder")
    ap.add_argument("--anchor-started-at", required=True,
                    help="ISO8601 started_at of the ANCHOR row (e.g. 2025-10-01T10:29:27.559790+00:00)")
    ap.add_argument("--anchor-wav", required=True,
                    help='WAV time of that anchor in HH:MM:SS (e.g. "03:45:57")')
    ap.add_argument("--run-id", required=True, help="Run ID (UUID) to filter transactions")
    ap.add_argument("--limit", type=int, default=0, help="Optional: limit number of rows (0 = no limit)")
    args = ap.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

    # Validate run_id
    try:
        _ = uuid.UUID(args.run_id)
    except ValueError:
        raise ValueError("--run-id must be a valid UUID")

    # Find WAV file in Downloads
    downloads_path = get_downloads_path()
    wav_path = os.path.join(downloads_path, args.wav_filename)
    
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"WAV not found in Downloads: {wav_path}")

    print(f"📁 Found WAV file: {wav_path}")

    # Compute T0 from anchor
    anchor_abs = iso_or_die(args.anchor_started_at)
    anchor_wav_seconds = parse_hms(args.anchor_wav)
    T0 = anchor_abs - timedelta(seconds=anchor_wav_seconds)
    print(f"🕐 Computed T0: {T0.isoformat()}")

    # Determine WAV duration (for clamping)
    wav_duration = get_wav_duration_seconds(wav_path)
    print(f"⏱️ WAV duration: {wav_duration:.1f} seconds")

    # Supabase client
    supabase: Client = create_client(url, key)

    # Derive a single Google Drive folder name for all clips using run date and anchor time
    try:
        run_row = supabase.table("runs").select("run_date").eq("id", args.run_id).limit(1).execute()
        run_date = (run_row.data[0]["run_date"] if run_row.data else anchor_abs.date().isoformat())
    except Exception:
        run_date = anchor_abs.date().isoformat()
    anchor_hhmm = anchor_abs.astimezone(timezone.utc).strftime("%H%M")
    clips_folder_name = f"Clips_{run_date}_{anchor_hhmm}"
    print(f"🗂️ Using Google Drive folder for all clips: {clips_folder_name}")

    # Build query for transactions
    query = supabase.table("transactions").select("id, started_at, ended_at").eq("run_id", args.run_id)

    if args.limit and args.limit > 0:
        query = query.limit(args.limit)

    resp = query.execute()
    rows = resp.data or []
    print(f"📋 Fetched {len(rows)} transactions from Supabase for run {args.run_id}.")

    # Create temporary directory for clips
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")

        made, skipped = 0, 0
        for row in rows:
            # Parse times
            if not row.get("started_at") or not row.get("ended_at"):
                skipped += 1
                continue

            tx_id = row["id"]
            t_s = dtparser.isoparse(row["started_at"]).astimezone(timezone.utc)
            t_e = dtparser.isoparse(row["ended_at"]).astimezone(timezone.utc)

            # Normalize timezone if missing (treat as UTC)
            if t_s.tzinfo is None:
                t_s = t_s.replace(tzinfo=timezone.utc)
            if t_e.tzinfo is None:
                t_e = t_e.replace(tzinfo=timezone.utc)

            # Normalize transactions to anchor date (use time-of-day alignment)
            anchor_date = (anchor_abs.astimezone(timezone.utc)).date()
            t_s = datetime(anchor_date.year, anchor_date.month, anchor_date.day, t_s.hour, t_s.minute, t_s.second, t_s.microsecond, tzinfo=timezone.utc)
            t_e = datetime(anchor_date.year, anchor_date.month, anchor_date.day, t_e.hour, t_e.minute, t_e.second, t_e.microsecond, tzinfo=timezone.utc)

            # Map to WAV seconds via T0
            raw_start = (t_s - T0).total_seconds()
            raw_end = (t_e - T0).total_seconds()

            # Enforce minimum duration of 1.0s when timestamps are equal or reversed
            if raw_end <= raw_start:
                raw_end = raw_start + 1.0

            # Clamp to [0, wav_duration]
            start_sec = max(0.0, min(raw_start, wav_duration))
            end_sec = max(0.0, min(raw_end, wav_duration))

            # If clamping collapses the window, skip
            if end_sec - start_sec <= 0.01:
                skipped += 1
                print(f"- SKIP {tx_id}: out of bounds after clamp "
                      f"(raw_start={raw_start:.3f}, raw_end={raw_end:.3f}, start={start_sec:.3f}, end={end_sec:.3f})")
                continue

            # Create clip in temp directory
            out_name = f"tx_{tx_id}.wav"
            out_path = os.path.join(temp_dir, out_name)

            try:
                # Cut the clip
                ffmpeg_cut(wav_path, out_path, start_sec, end_sec)
                print(f"✂️ Cut clip {tx_id} (start={start_sec:.3f}s, end={end_sec:.3f}s, dur={end_sec - start_sec:.3f}s)")
                
                # Upload clip to Google Drive
                clip_link = upload_to_gdrive_and_get_link(
                    out_path,
                    clips_folder_name,
                    out_name
                )
                
                if clip_link:
                    # Update transaction record with clip link
                    supabase.table("transactions").update({
                        "clip_s3_url": clip_link,  # Keep local path for reference
                    }).eq("id", tx_id).execute()
                    
                    made += 1
                    print(f"✅ Uploaded and linked {tx_id}: {clip_link}")
                else:
                    skipped += 1
                    print(f"❌ Failed to upload clip for {tx_id}")
                    
            except subprocess.CalledProcessError as e:
                skipped += 1
                print(f"❌ FFmpeg failed for {tx_id}: {e}")
            except Exception as e:
                skipped += 1
                print(f"❌ Error processing {tx_id}: {e}")

        print(f"🎉 Done! Processed {made} clips, skipped {skipped} rows.")


if __name__ == "__main__":
    main()