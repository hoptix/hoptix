#!/usr/bin/env python3
"""
Cut audio clips from a long MP3 based on Supabase transactions for a specific run.
Downloads MP3 from Google Drive URL and assumes transaction start time 10:00 maps to audio time 0:00.

Usage:
  export SUPABASE_URL="https://<your-project>.supabase.co"
  export SUPABASE_KEY="service_role_or_anon_key"

  python cut_run_audio.py \
      --gdrive-url "https://drive.google.com/file/d/FILE_ID/view" \
      --run-id UUID \
      [--limit 0]
"""

import argparse
import os
import subprocess
import uuid
import wave
import tempfile
import requests
import re
from datetime import datetime, timezone, timedelta
import dotenv

from dateutil import parser as dtparser
from supabase import create_client, Client
from integrations.gdrive_client import GoogleDriveClient

dotenv.load_dotenv()


def ffprobe_duration_seconds(wav_path: str) -> float:
    """Get WAV duration using ffprobe"""
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        wav_path
    ])
    return float(out.decode().strip())


def get_wav_duration_seconds(wav_path: str) -> float:
    """Get WAV duration, trying stdlib wave first, then ffprobe"""
    try:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
        return frames / float(rate)
    except wave.Error:
        return ffprobe_duration_seconds(wav_path)


def ffmpeg_cut(wav_path: str, out_path: str, start_sec: float, end_sec: float) -> None:
    """Cut audio clip using ffmpeg"""
    duration = max(0.0, end_sec - start_sec)
    if duration <= 0.0:
        return
    cmd = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-ss", f"{start_sec:.3f}",
        "-i", wav_path,
        "-t", f"{duration:.3f}",
        "-c", "copy",  # fast for WAV
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


def extract_file_id_from_gdrive_url(url: str) -> str:
    """Extract file ID from Google Drive URL"""
    # Handle different Google Drive URL formats
    patterns = [
        r'/file/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
        r'/d/([a-zA-Z0-9-_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract file ID from Google Drive URL: {url}")


def download_from_gdrive(file_id: str, output_path: str) -> bool:
    """Download file from Google Drive using file ID"""
    try:
        # Use gdown to download from Google Drive
        cmd = [
            "gdown",
            f"https://drive.google.com/uc?id={file_id}",
            "-O", output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Downloaded file to: {output_path}")
            return True
        else:
            print(f"❌ gdown failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ gdown not found. Please install it with: pip install gdown")
        return False
    except Exception as e:
        print(f"❌ Error downloading from Google Drive: {e}")
        return False


def get_downloads_path():
    """Get the Downloads folder path"""
    home = os.path.expanduser("~")
    downloads = os.path.join(home, "Downloads")
    return downloads


def time_to_seconds(time_str: str) -> float:
    """Convert HH:MM:SS or HH:MM:SS.microseconds to seconds"""
    try:
        # Handle both formats: HH:MM:SS and HH:MM:SS.microseconds
        if '.' in time_str:
            dt = datetime.strptime(time_str, "%H:%M:%S.%f")
        else:
            dt = datetime.strptime(time_str, "%H:%M:%S")
        
        return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1000000.0
    except ValueError as e:
        raise ValueError(f"Invalid time format '{time_str}'. Use HH:MM:SS or HH:MM:SS.microseconds") from e


def main():
    ap = argparse.ArgumentParser(description="Cut audio clips from MP3 based on transaction timestamps")
    ap.add_argument("--gdrive-url", required=True, help="Google Drive URL of the MP3 file")
    ap.add_argument("--run-id", required=True, help="Run ID (UUID) to filter transactions")
    ap.add_argument("--limit", type=int, default=0, help="Optional: limit number of rows (0 = no limit)")
    ap.add_argument("--reference-time", default="10:00:00", 
                    help="Reference time that maps to audio 0:00 (default: 10:00:00)")
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

    # Extract file ID from Google Drive URL
    try:
        file_id = extract_file_id_from_gdrive_url(args.gdrive_url)
        print(f"🔗 Extracted file ID: {file_id}")
    except ValueError as e:
        raise ValueError(f"Invalid Google Drive URL: {e}")

    # Download MP3 file to temporary location
    downloads_path = get_downloads_path()
    mp3_filename = f"run_{args.run_id[:8]}_audio.mp3"
    mp3_path = os.path.join(downloads_path, mp3_filename)
    
    print(f"📥 Downloading MP3 from Google Drive...")
    if not download_from_gdrive(file_id, mp3_path):
        raise RuntimeError(f"Failed to download MP3 from Google Drive")
    
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"Downloaded MP3 not found: {mp3_path}")

    print(f"📁 Found MP3 file: {mp3_path}")

    # Parse reference time (e.g., "10:00:00" -> 36000 seconds)
    reference_seconds = time_to_seconds(args.reference_time)
    print(f"🕐 Reference time: {args.reference_time} (maps to audio 0:00)")

    # Determine MP3 duration
    mp3_duration = get_wav_duration_seconds(mp3_path)  # ffprobe works for MP3 too
    print(f"⏱️ MP3 duration: {mp3_duration:.1f} seconds")

    # Supabase client
    supabase: Client = create_client(url, key)

    # Get run information for folder naming
    try:
        run_row = supabase.table("runs").select("run_date, location_id").eq("id", args.run_id).limit(1).execute()
        if run_row.data:
            run_date = run_row.data[0]["run_date"]
            location_id = run_row.data[0].get("location_id", "unknown")
        else:
            run_date = datetime.now().date().isoformat()
            location_id = "unknown"
    except Exception as e:
        print(f"⚠️ Could not fetch run details: {e}")
        run_date = datetime.now().date().isoformat()
        location_id = "unknown"

    # Create Google Drive folder name
    clips_folder_name = f"Run_{args.run_id[:8]}_{run_date}_{location_id}"
    print(f"🗂️ Using Google Drive folder: {clips_folder_name}")

    # Build query for transactions
    query = supabase.table("transactions").select("id, started_at, ended_at").eq("run_id", args.run_id)

    if args.limit and args.limit > 0:
        query = query.limit(args.limit)

    resp = query.execute()
    rows = resp.data or []
    print(f"📋 Fetched {len(rows)} transactions from Supabase for run {args.run_id}.")

    if not rows:
        print("❌ No transactions found for this run ID")
        return

    # Create temporary directory for clips
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")

        made, skipped = 0, 0
        for row in rows:
            # Parse times
            if not row.get("started_at") or not row.get("ended_at"):
                skipped += 1
                print(f"- SKIP {row.get('id', 'unknown')}: missing timestamps")
                continue

            tx_id = row["id"]
            started_at = row["started_at"]
            ended_at = row["ended_at"]

            # Parse the timestamps
            try:
                start_dt = dtparser.isoparse(started_at)
                end_dt = dtparser.isoparse(ended_at)
            except Exception as e:
                skipped += 1
                print(f"- SKIP {tx_id}: invalid timestamp format - {e}")
                continue

            # Extract time components (HH:MM:SS.microseconds)
            start_time_str = start_dt.strftime("%H:%M:%S.%f")
            end_time_str = end_dt.strftime("%H:%M:%S.%f")

            # Convert to seconds
            start_seconds = time_to_seconds(start_time_str)
            end_seconds = time_to_seconds(end_time_str)

            # Map to audio timeline: subtract reference time
            audio_start = start_seconds - reference_seconds
            audio_end = end_seconds - reference_seconds

            # Enforce minimum duration of 1.0s when timestamps are equal or reversed
            if audio_end <= audio_start:
                audio_end = audio_start + 1.0

            # Clamp to [0, mp3_duration]
            start_sec = max(0.0, min(audio_start, mp3_duration))
            end_sec = max(0.0, min(audio_end, mp3_duration))

            # If clamping collapses the window, skip
            if end_sec - start_sec <= 0.01:
                skipped += 1
                print(f"- SKIP {tx_id}: out of bounds after clamp "
                      f"(audio_start={audio_start:.3f}, audio_end={audio_end:.3f}, start={start_sec:.3f}, end={end_sec:.3f})")
                continue

            # Create clip in temp directory
            out_name = f"tx_{tx_id}.wav"
            out_path = os.path.join(temp_dir, out_name)

            try:
                # Cut the clip
                ffmpeg_cut(mp3_path, out_path, start_sec, end_sec)
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
                        "clip_s3_url": clip_link,
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
        print(f"📁 All clips uploaded to Google Drive folder: {clips_folder_name}")
        
        # Clean up downloaded MP3 file
        try:
            os.remove(mp3_path)
            print(f"🗑️ Cleaned up downloaded MP3: {mp3_path}")
        except Exception as e:
            print(f"⚠️ Could not clean up MP3 file: {e}")


if __name__ == "__main__":
    main()
