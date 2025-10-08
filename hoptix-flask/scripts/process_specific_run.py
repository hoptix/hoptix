#!/usr/bin/env python3
"""
Script to process audio for run 3afe854f-6cf6-403e-b2b2-77e039b6f8ca
with proper anchor mapping from Google Drive MP3.

This script:
1. Downloads the MP3 from Google Drive
2. Converts it to WAV format  
3. Finds the correct anchor transaction in the database
4. Executes the audio cutting process with proper mapping
5. Cleans up temporary files

Usage:
  export SUPABASE_URL="https://<your-project>.supabase.co"
  export SUPABASE_KEY="service_role_or_anon_key"
  
  python process_specific_run.py
"""

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
import dotenv

# Add the parent directory to the Python path so we can import from integrations
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client
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


def find_anchor_transaction(supabase: Client, run_id: str, target_time_str: str) -> dict:
    """
    Find a transaction that started at approximately the target time (10:00:00).
    Returns the transaction data and the actual started_at time.
    """
    try:
        # Get all transactions for this run
        resp = supabase.table("transactions").select("id, started_at, ended_at").eq("run_id", run_id).execute()
        transactions = resp.data or []
        
        if not transactions:
            raise ValueError(f"No transactions found for run {run_id}")
        
        print(f"📋 Found {len(transactions)} transactions for run {run_id}")
        
        # Parse target time (HH:MM:SS)
        target_hour, target_minute, target_second = map(int, target_time_str.split(":"))
        
        # Find the transaction closest to the target time
        best_match = None
        min_time_diff = float('inf')
        
        for tx in transactions:
            if not tx.get("started_at"):
                continue
                
            # Parse the transaction start time
            tx_start = datetime.fromisoformat(tx["started_at"].replace('Z', '+00:00'))
            
            # Calculate time difference in seconds
            tx_hour = tx_start.hour
            tx_minute = tx_start.minute
            tx_second = tx_start.second
            
            # Calculate absolute difference in seconds
            time_diff = abs((tx_hour - target_hour) * 3600 + 
                          (tx_minute - target_minute) * 60 + 
                          (tx_second - target_second))
            
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                best_match = tx
        
        if best_match is None:
            raise ValueError(f"No suitable anchor transaction found near {target_time_str}")
        
        print(f"🎯 Found anchor transaction: {best_match['id']} at {best_match['started_at']}")
        print(f"⏱️ Time difference from target: {min_time_diff} seconds")
        
        return best_match
        
    except Exception as e:
        print(f"❌ Error finding anchor transaction: {e}")
        raise


def get_downloads_path():
    """Get the Downloads folder path"""
    home = os.path.expanduser("~")
    downloads = os.path.join(home, "Downloads")
    return downloads


def main():
    # Configuration
    RUN_ID = "3afe854f-6cf6-403e-b2b2-77e039b6f8ca"
    GDRIVE_FILE_ID = "1yugQLuOMt8Jm3zQEwoX02P057of3ooum"
    ANCHOR_TRANSACTION_TIME = "10:00:00"  # Transaction time that corresponds to 0:00 video time
    ANCHOR_VIDEO_TIME = "00:00:00"        # Video time that corresponds to the anchor transaction

    print(f"🎯 Processing run: {RUN_ID}")
    print(f"📁 Google Drive file ID: {GDRIVE_FILE_ID}")
    print(f"⏰ Anchor mapping: transaction {ANCHOR_TRANSACTION_TIME} = video {ANCHOR_VIDEO_TIME}")

    # Validate environment variables
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) must be set in environment")

    # Initialize Supabase client
    supabase: Client = create_client(url, key)

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Download MP3 from Google Drive
        mp3_filename = f"run_{RUN_ID}.mp3"
        mp3_path = os.path.join(temp_dir, mp3_filename)
        
        print("📥 Downloading MP3 from Google Drive...")
        if not download_mp3_from_gdrive(GDRIVE_FILE_ID, mp3_path):
            print("❌ Failed to download MP3 file")
            return 1

        # Convert MP3 to WAV
        wav_filename = f"run_{RUN_ID}.wav"
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

        # Find the anchor transaction in the database
        print("🔍 Finding anchor transaction in database...")
        anchor_tx = find_anchor_transaction(supabase, RUN_ID, ANCHOR_TRANSACTION_TIME)
        
        # Use the actual started_at time from the database
        anchor_started_at = anchor_tx["started_at"]

        print(f"🕐 Using anchor started_at: {anchor_started_at}")
        print(f"🎬 Using anchor WAV time: {ANCHOR_VIDEO_TIME}")

        # Execute the cutting script
        print("✂️ Starting audio cutting process...")
        
        cut_script_path = os.path.join(os.path.dirname(__file__), "..", "services", "cut_tx_audio_supabase.py")
        
        cmd = [
            "python", cut_script_path,
            "--wav-filename", wav_filename,
            "--anchor-started-at", anchor_started_at,
            "--anchor-wav", ANCHOR_VIDEO_TIME,
            "--run-id", RUN_ID
        ]
        
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
