#!/bin/bash
# Safe wrapper for voice diarization job with validation and error handling

set -e  # Exit on error

echo "🚀 Starting Voice Diarization Job"
echo "================================"

# Run validation first
echo ""
echo "📋 Running pre-flight checks..."
python /app/scripts/validate_voice_setup.py

if [ $? -ne 0 ]; then
    echo "❌ Validation failed. Exiting."
    exit 1
fi

echo ""
echo "✅ Validation passed. Starting main job..."
echo ""

# Parse arguments (location_id, date, options)
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <location_id> <date> [options]"
    echo "Example: $0 c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06"
    exit 1
fi

LOCATION_ID=$1
DATE=$2
shift 2  # Remove first two args, keep any additional options

# Run the main job with error handling
echo "📍 Processing location: $LOCATION_ID"
echo "📅 Date: $DATE"
echo ""

# Execute with timeout (6 hours max) and capture exit code
timeout 6h python /app/scripts/run_voice_diarization.py "$LOCATION_ID" "$DATE" "$@" || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "❌ Job timed out after 6 hours"
    else
        echo "❌ Job failed with exit code: $EXIT_CODE"
    fi
    exit $EXIT_CODE
}

echo ""
echo "✅ Voice diarization job completed successfully!"
exit 0