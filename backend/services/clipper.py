import os
import subprocess
import wave
import tempfile
from datetime import datetime, timezone, timedelta
from dateutil import parser as dtparser
from services.database import Supa
from services.gdrive import GoogleDriveClient

db = Supa()
gdrive = GoogleDriveClient()

def ffprobe_duration_seconds(wav_path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        wav_path
    ])
    return float(out.decode().strip())


def get_audio_duration_seconds(audio_path: str) -> float:
    # Use ffprobe for all audio formats (MP3, WAV, etc.)
    return ffprobe_duration_seconds(audio_path)


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


def ffmpeg_cut(audio_path: str, out_path: str, start_sec: float, end_sec: float) -> None:
    duration = max(0.0, end_sec - start_sec)
    if duration <= 0.0:
        return
    cmd = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-ss", f"{start_sec:.3f}",
        "-i", audio_path,
        "-t", f"{duration:.3f}",
        "-acodec", "libmp3lame",  # MP3 encoding
        "-b:a", "192k",  # 192kbps bitrate
        "-ar", "44100",  # 44.1kHz sample rate
        "-ac", "2",  # stereo
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

def clip_transactions(run_id: str, audio_path: str, date: str, anchor_audio: str = "00:00:00",  time_of_day_started_at: str = "10:00:00Z", limit: int = 0):

    print(f"📁 Found audio file: {audio_path}")

    anchor_started_at = f"{date}T{time_of_day_started_at}"
    print(f"🕐 Anchor started at: {anchor_started_at}")
    # Compute T0 from anchor
    anchor_abs = iso_or_die(anchor_started_at)
    anchor_audio_seconds = parse_hms(anchor_audio)
    T0 = anchor_abs - timedelta(seconds=anchor_audio_seconds)
    print(f"🕐 Computed T0: {T0.isoformat()}")

    # Determine audio duration (for clamping)
    audio_duration = get_audio_duration_seconds(audio_path)
    print(f"⏱️ Audio duration: {audio_duration:.1f} seconds")

    # Derive a single Google Drive folder name for all clips using run date and anchor time
    try:
        run_date = db.get_run(run_id)["run_date"]

    except Exception:
        run_date = anchor_abs.date().isoformat()


    anchor_hhmm = anchor_abs.astimezone(timezone.utc).strftime("%H%M")
    clips_folder_name = f"Clips_{run_date}_{anchor_hhmm}"
    print(f"🗂️ Using Google Drive folder for all clips: {clips_folder_name}")

    # Build query for transactions
    query = db.get_transactions(run_id, limit)

    rows = query or []
    print(f"📋 Fetched {len(rows)} transactions from Supabase for run {run_id}.")

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

            # Clamp to [0, audio_duration]
            start_sec = max(0.0, min(raw_start, audio_duration))
            end_sec = max(0.0, min(raw_end, audio_duration))

            # If clamping collapses the window, skip
            if end_sec - start_sec <= 0.01:
                skipped += 1
                print(f"- SKIP {tx_id}: out of bounds after clamp "
                      f"(raw_start={raw_start:.3f}, raw_end={raw_end:.3f}, start={start_sec:.3f}, end={end_sec:.3f})")
                continue

            # Create clip in temp directory
            out_name = f"tx_{tx_id}.mp3"
            out_path = os.path.join(temp_dir, out_name)

            try:
                # Cut the clip
                ffmpeg_cut(audio_path, out_path, start_sec, end_sec)
                print(f"✂️ Cut clip {tx_id} (start={start_sec:.3f}s, end={end_sec:.3f}s, dur={end_sec - start_sec:.3f}s)")
                
                # Upload clip to Google Drive
                clip_link = upload_to_gdrive_and_get_link(
                    out_path,
                    clips_folder_name,
                    out_name
                )
                
                if clip_link:
                    # Update transaction record with clip link
                    db.update_transaction(tx_id, {
                        "clip_s3_url": clip_link,  # Keep local path for reference
                    })
                    
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

