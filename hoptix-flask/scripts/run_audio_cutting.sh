#!/bin/bash

# Script to execute audio cutting for run 99816083-f6bd-48cf-9b4b-2a8df27c8ec4
# Downloads MP3 from Google Drive and processes transactions

set -e  # Exit on any error

# Configuration
RUN_ID="26534cd7-d097-4510-959f-6dfe35be1323"
GDRIVE_FILE_ID="1r42Gvh8roy5hRlge7a3Kk1eHuRF-c8Sj"
ANCHOR_TRANSACTION_TIME="07:00:00"
ANCHOR_VIDEO_TIME="00:00:00"

# File paths
DOWNLOADS_DIR="$HOME/Downloads"
MP3_FILENAME="audio_2025-10-07_10-00-03.mp3"
MP3_PATH="$DOWNLOADS_DIR/$MP3_FILENAME"

echo "🎯 Processing run: $RUN_ID"
echo "📁 Google Drive file ID: $GDRIVE_FILE_ID"
echo "⏰ Anchor mapping: transaction $ANCHOR_TRANSACTION_TIME = video $ANCHOR_VIDEO_TIME"

# Load environment variables from .env file
if [ -f "$(dirname "$0")/../.env" ]; then
    echo "📋 Loading environment variables from .env file..."
    # Load only SUPABASE variables to avoid parsing issues
    while IFS='=' read -r key value; do
        if [[ "$key" == "SUPABASE_URL" || "$key" == "SUPABASE_KEY" ]]; then
            export "$key=$value"
        fi
    done < <(grep -E '^SUPABASE_(URL|KEY)=' "$(dirname "$0")/../.env")
fi

# Check if required environment variables are set
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in environment"
    echo "   Make sure .env file exists in hoptix-flask directory"
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

# Function to validate MP3 file
validate_mp3() {
    echo "🔍 Validating MP3 file..."
    
    if ! command -v ffprobe &> /dev/null; then
        echo "❌ Error: ffprobe is not installed"
        exit 1
    fi
    
    # Check if file exists and is valid
    if [ ! -f "$MP3_PATH" ]; then
        echo "❌ Error: MP3 file not found: $MP3_PATH"
        exit 1
    fi
    
    # Get file info
    duration=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$MP3_PATH")
    size=$(du -h "$MP3_PATH" | cut -f1)
    
    echo "✅ MP3 file validated:"
    echo "   📁 Path: $MP3_PATH"
    echo "   ⏱️  Duration: ${duration}s"
    echo "   📊 Size: $size"
}

# Function to clean up files
cleanup() {
    echo "🧹 Cleaning up temporary files..."
    # Only remove MP3 if it was downloaded (not if it already existed)
    if [ "$DOWNLOADED_MP3" = "true" ] && [ -f "$MP3_PATH" ]; then
        rm -f "$MP3_PATH"
        echo "🗑️ Removed downloaded MP3 file"
    else
        echo "📁 Keeping existing MP3 file: $MP3_PATH"
    fi
}

# Set up cleanup on exit
trap cleanup EXIT

# Main execution
echo "📁 Using Downloads directory: $DOWNLOADS_DIR"

# Check if MP3 file already exists locally
if [ -f "$MP3_PATH" ]; then
    echo "✅ Found existing MP3 file: $MP3_PATH"
    DOWNLOADED_MP3="false"
    validate_mp3
else
    echo "📥 MP3 file not found locally, downloading from Google Drive..."
    DOWNLOADED_MP3="true"
    download_mp3
    validate_mp3
fi

# Execute the cutting script
echo "✂️ Starting audio cutting process..."

# Calculate anchor parameters
# We need to create a proper anchor timestamp
# For now, we'll use a placeholder that assumes the run is from today
ANCHOR_STARTED_AT=$(date -u +"%Y-%m-%dT${ANCHOR_TRANSACTION_TIME}.000000+00:00")

echo "🕐 Using anchor started_at: $ANCHOR_STARTED_AT"
echo "🎬 Using anchor MP3 time: $ANCHOR_VIDEO_TIME"

# Run the cutting script
cd "$(dirname "$0")/.."
source venv/bin/activate
python services/cut_tx_audio_supabase.py \
    --mp3-filename "$MP3_FILENAME" \
    --anchor-started-at "$ANCHOR_STARTED_AT" \
    --anchor-mp3 "$ANCHOR_VIDEO_TIME" \
    --run-id "$RUN_ID"

echo "🎉 Audio processing completed successfully!"
