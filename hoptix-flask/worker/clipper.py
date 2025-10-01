# hoptix-flask/worker/clipper.py
import os
import shutil
import tempfile
import subprocess
import datetime as dt
from typing import Dict
from integrations.s3_client import put_file
from integrations.gdrive_client import GoogleDriveClient
from dateutil import parser as dateparse

FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")

def generate_run_name(db, run_id: str) -> str:
    """Generate descriptive run name: Org_Location_YYYY_MM_DD"""
    try:
        # Query run -> location -> org to get names and date
        result = db.client.table("runs").select(
            "run_date, locations!inner(name, orgs!inner(name))"
        ).eq("id", run_id).limit(1).execute()
        
        if not result.data:
            print(f"No data found for run_id: {run_id}")
            return run_id
        
        run_data = result.data[0]
        location_data = run_data.get("locations")
        org_data = location_data.get("orgs") if location_data else None
        
        org_name = org_data.get("name") if org_data else "Unknown"
        location_name = location_data.get("name") if location_data else "Unknown"
        run_date = run_data.get("run_date", "1970-01-01")
        
        # Clean names (remove spaces, special chars)
        org_clean = "".join(c for c in org_name if c.isalnum())
        location_clean = "".join(c for c in location_name if c.isalnum())
        
        # Parse run date and format as YYYY_MM_DD  
        date_obj = dateparse.parse(run_date).date()
        date_str = date_obj.strftime("%Y_%m_%d")
        
        return f"{org_clean}_{location_clean}_{date_str}"
        
    except Exception as e:
        # Fallback to run_id if anything fails
        print(f"Error generating run name for run_id {run_id}: {e}")
        print(f"Using fallback run_id: {run_id}")
        return run_id

def generate_video_name(transaction_started_at: str, transaction_ended_at: str) -> str:
    """Generate video name: HH_StartMM_EndMM using transaction timestamps"""
    try:
        start_dt = dateparse.isoparse(transaction_started_at)
        end_dt = dateparse.isoparse(transaction_ended_at)
        
        hour = start_dt.strftime("%H")
        start_min = start_dt.strftime("%M")
        end_min = end_dt.strftime("%M")
        
        # Debug logging
        print(f"Video name debug:")
        print(f"  Transaction started_at: {transaction_started_at}")
        print(f"  Transaction ended_at: {transaction_ended_at}")
        print(f"  Generated name: {hour}_{start_min}_{end_min}")
        
        return f"{hour}_{start_min}_{end_min}"
        
    except Exception as e:
        # Fallback using transaction start time if possible
        print(f"Error generating video name: {e}")
        try:
            fallback_dt = dateparse.isoparse(transaction_started_at)
            return f"video_{fallback_dt.strftime('%H_%M')}"
        except:
            return f"video_unknown"

def generate_full_clip_url(deriv_bucket: str, region: str, clip_key: str) -> str:
    """Generate full S3 URL"""
    return f"https://{deriv_bucket}.s3.{region}.amazonaws.com/{clip_key}"

def _sec(dtobj: dt.datetime) -> float:
    # seconds since epoch (float) – only used when computing offsets
    return dtobj.timestamp()

def _ffmpeg_trim_copy(input_path: str, start_sec: float, end_sec: float, out_path: str) -> None:
    """
    Fastest path: keyframe-aligned stream copy (no re-encode).
    If your cuts land off keyframes you might see ~1s drift. If that’s a problem,
    flip REENCODE_CLIPS=yes in env to force precise re-encode.
    """
    duration = max(0.1, end_sec - start_sec)
    # ss before -i = fast seek; -t duration; -c copy for stream copy
    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", f"{start_sec:.3f}",
        "-i", input_path,
        "-t", f"{duration:.3f}",
        "-c", "copy",
        out_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _ffmpeg_trim_reencode(input_path: str, start_sec: float, end_sec: float, out_path: str) -> None:
    """
    Precise but slower: re-encode video to H.264 + AAC so the cut is exact.
    """
    duration = max(0.1, end_sec - start_sec)
    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", f"{start_sec:.3f}",
        "-i", input_path,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def cut_clip_for_transaction(
    db, input_video_local: str,
    video_started_at_iso: str, video_ended_at_iso: str, tx_row: Dict, run_id: str, video_id: str
) -> str:
    """
    Extracts audio from video clip and saves it locally.
    Returns the local audio file path instead of Google Drive file ID.
    tx_row fields expected: id, started_at, ended_at
    """
    # Videos are hour-long segments, extract minutes:seconds from transaction times
    t0 = dateparse.isoparse(tx_row["started_at"])
    t1 = dateparse.isoparse(tx_row["ended_at"])
    
    # Extract minutes and seconds from transaction timestamps
    # Example: if transaction is at 12:34:15, we want 34*60 + 15 = 2055 seconds from start of hour
    start_minutes = t0.minute
    start_seconds = t0.second + t0.microsecond / 1_000_000
    
    end_minutes = t1.minute  
    end_seconds = t1.second + t1.microsecond / 1_000_000
    
    # Convert to seconds from start of the hour
    start_off = start_minutes * 60 + start_seconds
    end_off = end_minutes * 60 + end_seconds
    
    # Handle case where transaction crosses hour boundary (end < start)
    if end_off < start_off:
        end_off += 3600  # Add 1 hour worth of seconds
    
    # Debug logging for clip timing
    duration = end_off - start_off
    print(f"Clip timing debug:")
    print(f"  Video start: {video_started_at_iso}")
    print(f"  Transaction start: {tx_row['started_at']}")
    print(f"  Transaction end: {tx_row['ended_at']}")
    print(f"  Start offset: {start_off:.3f}s")
    print(f"  End offset: {end_off:.3f}s")
    print(f"  Clip duration: {duration:.3f}s")
    
    # Ensure minimum duration
    if duration < 1.0:
        print(f"Warning: Very short clip duration ({duration:.3f}s), extending to 1.0s")
        end_off = start_off + 1.0

    # Create audio clips directory
    audio_clips_dir = "transaction_audio_clips"
    os.makedirs(audio_clips_dir, exist_ok=True)
    
    # Generate descriptive names
    run_name = generate_run_name(db, run_id)
    video_name = generate_video_name(tx_row["started_at"], tx_row["ended_at"])
    
    # Create audio file path
    audio_filename = f"{video_name}_tx={tx_row['id']}.mp3"
    audio_path = os.path.join(audio_clips_dir, audio_filename)
    
    print(f"🎵 Extracting audio clip: {audio_path}")
    print(f"   📍 From video: {input_video_local}")
    print(f"   ⏱️ Time range: {start_off:.3f}s - {end_off:.3f}s ({duration:.3f}s)")
    
    # Extract audio directly from video using FFmpeg
    try:
        cmd = [
            FFMPEG_BIN, "-y",
            "-ss", f"{start_off:.3f}",
            "-i", input_video_local,
            "-t", f"{duration:.3f}",
            "-vn",  # No video
            "-acodec", "mp3",
            "-ab", "128k",  # Audio bitrate
            "-ar", "44100",  # Sample rate
            audio_path
        ]
        
        print(f"🔧 Running FFmpeg command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Verify the audio file was created
        if os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            print(f"✅ Audio clip saved: {audio_path} ({file_size:,} bytes)")
            return audio_path
        else:
            print(f"❌ Audio file was not created: {audio_path}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed to extract audio: {e}")
        return None
    except Exception as e:
        print(f"❌ Error extracting audio: {e}")
        return None


def upload_clip_to_gdrive(local_clip_path: str, run_name: str, clip_name: str) -> str:
    """
    Upload a clip to Google Drive and return the file ID.
    """
    try:
        gdrive = GoogleDriveClient()
        
        # Create folder name for video clips
        folder_name = f"{run_name}_clips"
        
        # Upload to Google Drive
        file_id = gdrive.upload_file(local_clip_path, folder_name, clip_name)
        
        if file_id:
            print(f"✅ Uploaded clip to Google Drive: {file_id}")
            return file_id
        else:
            print(f"❌ Failed to upload clip to Google Drive")
            return None
            
    except Exception as e:
        print(f"❌ Error uploading clip to Google Drive: {e}")
        return None

def update_tx_meta_with_clip(db, tx_id: str, audio_file_path: str, speaker_info: dict = None):
    """Update transaction with audio file path and speaker information"""
    # Store the audio file path in the clip_s3_url field (reusing the field for audio path)
    update_data = {"clip_s3_url": audio_file_path}
    print(f"💾 Updating transaction {tx_id} with audio file: {audio_file_path}")
    if speaker_info:
        update_data["speaker_info"] = speaker_info
        print(f"🎤 Adding speaker info: {speaker_info}")
    
    db.client.table("transactions").update(update_data).eq("id", tx_id).execute()
    print(f"✅ Transaction {tx_id} updated successfully")