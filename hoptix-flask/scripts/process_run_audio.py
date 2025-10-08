#!/usr/bin/env python3
"""
Script to process audio for a specific run by downloading from Google Drive
and cutting transaction clips using the cut_tx_audio_supabase.py functionality.

This script:
1. Downloads the MP3 file from Google Drive
2. Converts it to WAV format
3. Executes the audio cutting process with proper anchor mapping
4. Cleans up temporary files

Usage:
  export SUPABASE_URL="https://<your-project>.supabase.co"
  export SUPABASE_KEY="service_role_or_anon_key"
  
  python process_run_audio.py \
      --run-id "3afe854f-6cf6-403e-b2b2-77e039b6f8ca" \
      --gdrive-file-id "1yugQLuOMt8Jm3zQEwoX02P057of3ooum" \
      --anchor-transaction-time "10:00:00" \
      --anchor-video-time "00:00:00"
"""

import argparse
import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
import dotenv

# Add the parent directory to the Python path so we can import from integrations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.gdrive_client import GoogleDriveClient

dotenv.load_dotenv()


def download_mp3_from_gdrive(file_id: str, local_path: str) -> bool:
    """Download MP3 file from Google Drive"""
    try:
        gdrive = GoogleDriveClient()
        success = gdrive.download_file(file_id, local_path)
        if success:
            print(f"✅ Downloaded MP3 file to: {local_path}")
            return True
        else:
            print(f"❌ Failed to download MP3 file")
            return False
    except Exception as e:
        print(f"❌ Error downloading MP3: {e}")
        return False


def convert_mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
    """Convert MP3 to WAV using ffmpeg"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", mp3_path,
            "-acodec", "pcm_s16le",  # 16-bit PCM
            "-ar", "44100",  # 44.1kHz sample rate
            wav_path
        ]
        subprocess.run(cmd, check=True)
        print(f"✅ Converted MP3 to WAV: {wav_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg conversion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error converting MP3 to WAV: {e}")
        return False


def get_downloads_path():
    """Get the Downloads folder path"""
    home = os.path.expanduser("~")
    downloads = os.path.join(home, "Downloads")
    return downloads


def parse_time_to_seconds(time_str: str) -> int:
    """Parse HH:MM:SS time string to seconds"""
    parts = time_str.split(":")
    if len(parts) != 3:
        raise ValueError("Time must be in HH:MM:SS format")
    h, m, s = parts
    return int(h) * 3600 + int(m) * 60 + int(s)


def main():
    ap = argparse.ArgumentParser(description="Process audio for a specific run")
    ap.add_argument("--run-id", required=True, help="Run ID (UUID) to process")
    ap.add_argument("--gdrive-file-id", required=True, help="Google Drive file ID of the MP3")
    ap.add_argument("--anchor-transaction-time", required=True, 
                    help="Transaction time that corresponds to anchor (HH:MM:SS)")
    ap.add_argument("--anchor-video-time", required=True,
                    help="Video time that corresponds to anchor (HH:MM:SS)")
    ap.add_argument("--limit", type=int, default=0, help="Optional: limit number of transactions (0 = no limit)")
    args = ap.parse_args()

    # Validate environment variables
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

    print(f"🎯 Processing run: {args.run_id}")
    print(f"📁 Google Drive file ID: {args.gdrive_file_id}")
    print(f"⏰ Anchor mapping: transaction {args.anchor_transaction_time} = video {args.anchor_video_time}")

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Download MP3 from Google Drive
        mp3_filename = f"run_{args.run_id}.mp3"
        mp3_path = os.path.join(temp_dir, mp3_filename)
        
        print("📥 Downloading MP3 from Google Drive...")
        if not download_mp3_from_gdrive(args.gdrive_file_id, mp3_path):
            print("❌ Failed to download MP3 file")
            return 1

        # Convert MP3 to WAV
        wav_filename = f"run_{args.run_id}.wav"
        wav_path = os.path.join(temp_dir, wav_filename)
        
        print("🔄 Converting MP3 to WAV...")
        if not convert_mp3_to_wav(mp3_path, wav_path):
            print("❌ Failed to convert MP3 to WAV")
            return 1

        # Copy WAV to Downloads folder for the cutting script
        downloads_path = get_downloads_path()
        downloads_wav_path = os.path.join(downloads_path, wav_filename)
        
        print(f"📋 Copying WAV to Downloads: {downloads_wav_path}")
        shutil.copy2(wav_path, downloads_wav_path)

        # Calculate anchor parameters for the cutting script
        # We need to find a transaction that started at the anchor transaction time
        # and map it to the anchor video time
        
        # For now, we'll use a placeholder anchor timestamp
        # In a real scenario, you'd query the database to find the actual transaction
        # that started at the anchor transaction time
        
        # Parse the anchor times
        anchor_tx_seconds = parse_time_to_seconds(args.anchor_transaction_time)
        anchor_video_seconds = parse_time_to_seconds(args.anchor_video_time)
        
        # Create a placeholder anchor timestamp (you may need to adjust this)
        # This assumes the run is from today and the anchor transaction started at the specified time
        today = datetime.now(timezone.utc).date()
        anchor_started_at = datetime.combine(today, datetime.min.time().replace(
            hour=int(args.anchor_transaction_time.split(":")[0]),
            minute=int(args.anchor_transaction_time.split(":")[1]),
            second=int(args.anchor_transaction_time.split(":")[2])
        ), tzinfo=timezone.utc)
        
        # Format the anchor video time as HH:MM:SS
        anchor_wav_time = args.anchor_video_time

        print(f"🕐 Using anchor started_at: {anchor_started_at.isoformat()}")
        print(f"🎬 Using anchor WAV time: {anchor_wav_time}")

        # Execute the cutting script
        print("✂️ Starting audio cutting process...")
        
        cut_script_path = os.path.join(os.path.dirname(__file__), "..", "services", "cut_tx_audio_supabase.py")
        
        cmd = [
            "python", cut_script_path,
            "--wav-filename", wav_filename,
            "--anchor-started-at", anchor_started_at.isoformat(),
            "--anchor-wav", anchor_wav_time,
            "--run-id", args.run_id
        ]
        
        if args.limit > 0:
            cmd.extend(["--limit", str(args.limit)])
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ Audio cutting completed successfully!")
            print("📊 Output:")
            print(result.stdout)
            if result.stderr:
                print("⚠️ Warnings/Errors:")
                print(result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"❌ Audio cutting failed: {e}")
            print("📊 Error output:")
            print(e.stdout)
            print(e.stderr)
            return 1

        # Clean up the WAV file from Downloads
        try:
            if os.path.exists(downloads_wav_path):
                os.remove(downloads_wav_path)
                print(f"🧹 Cleaned up temporary WAV file: {downloads_wav_path}")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up temporary file: {e}")

    print("🎉 Audio processing completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
