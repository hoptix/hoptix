#!/bin/bash

# Script to execute audio cutting for run 3afe854f-6cf6-403e-b2b2-77e039b6f8ca
# Downloads MP3 from Google Drive, converts to WAV, and processes transactions

set -e  # Exit on any error

# Configuration
RUN_ID="3afe854f-6cf6-403e-b2b2-77e039b6f8ca"
GDRIVE_FILE_ID="1yugQLuOMt8Jm3zQEwoX02P057of3ooum"
ANCHOR_TRANSACTION_TIME="10:00:00"
ANCHOR_VIDEO_TIME="00:00:00"

# File paths
DOWNLOADS_DIR="$HOME/Downloads"
MP3_FILENAME="run_${RUN_ID}.mp3"
WAV_FILENAME="run_${RUN_ID}.wav"
MP3_PATH="$DOWNLOADS_DIR/$MP3_FILENAME"
WAV_PATH="$DOWNLOADS_DIR/$WAV_FILENAME"

echo "🎯 Processing run: $RUN_ID"
echo "📁 Google Drive file ID: $GDRIVE_FILE_ID"
echo "⏰ Anchor mapping: transaction $ANCHOR_TRANSACTION_TIME = video $ANCHOR_VIDEO_TIME"

# Check if required environment variables are set
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in environment"
    exit 1
fi

# Function to download MP3 from Google Drive
download_mp3() {
    echo "📥 Downloading MP3 from Google Drive..."
    
    # Create a Python script to download the file
    cat > /tmp/download_mp3.py << 'EOF'
import sys
import os
from integrations.gdrive_client import GoogleDriveClient

def main():
    if len(sys.argv) != 3:
        print("Usage: python download_mp3.py <file_id> <output_path>")
        sys.exit(1)
    
    file_id = sys.argv[1]
    output_path = sys.argv[2]
    
    try:
        gdrive = GoogleDriveClient()
        success = gdrive.download_file(file_id, output_path)
        if success:
            print(f"✅ Downloaded MP3 file to: {output_path}")
            sys.exit(0)
        else:
            print("❌ Failed to download MP3 file")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error downloading MP3: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

    # Run the download script
    cd "$(dirname "$0")/.."
    python /tmp/download_mp3.py "$GDRIVE_FILE_ID" "$MP3_PATH"
    
    # Clean up
    rm -f /tmp/download_mp3.py
}

# Function to convert MP3 to WAV
convert_mp3_to_wav() {
    echo "🔄 Converting MP3 to WAV..."
    
    if ! command -v ffmpeg &> /dev/null; then
        echo "❌ Error: ffmpeg is not installed"
        exit 1
    fi
    
    ffmpeg -y -hide_banner -loglevel error \
        -i "$MP3_PATH" \
        -acodec pcm_s16le \
        -ar 44100 \
        "$WAV_PATH"
    
    echo "✅ Converted MP3 to WAV: $WAV_PATH"
}

# Function to clean up files
cleanup() {
    echo "🧹 Cleaning up temporary files..."
    [ -f "$MP3_PATH" ] && rm -f "$MP3_PATH"
    [ -f "$WAV_PATH" ] && rm -f "$WAV_PATH"
}

# Set up cleanup on exit
trap cleanup EXIT

# Main execution
echo "📁 Using Downloads directory: $DOWNLOADS_DIR"

# Download MP3
download_mp3

# Convert to WAV
convert_mp3_to_wav

# Execute the cutting script
echo "✂️ Starting audio cutting process..."

# Calculate anchor parameters
# We need to create a proper anchor timestamp
# For now, we'll use a placeholder that assumes the run is from today
ANCHOR_STARTED_AT=$(date -u +"%Y-%m-%dT${ANCHOR_TRANSACTION_TIME}.000000+00:00")

echo "🕐 Using anchor started_at: $ANCHOR_STARTED_AT"
echo "🎬 Using anchor WAV time: $ANCHOR_VIDEO_TIME"

# Run the cutting script
cd "$(dirname "$0")/.."
python services/cut_tx_audio_supabase.py \
    --wav-filename "$WAV_FILENAME" \
    --anchor-started-at "$ANCHOR_STARTED_AT" \
    --anchor-wav "$ANCHOR_VIDEO_TIME" \
    --run-id "$RUN_ID"

echo "🎉 Audio processing completed successfully!"
