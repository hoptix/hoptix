#!/bin/bash
# Run voice diarization for today's date automatically
# Usage: ./run_voice_today.sh <location_id>

set -e

LOCATION_ID=${1:-$LOCATION_ID}

if [ -z "$LOCATION_ID" ]; then
    echo "❌ Error: LOCATION_ID required"
    echo "Usage: $0 <location_id>"
    echo "Or set LOCATION_ID environment variable"
    exit 1
fi

# Get today's date in YYYY-MM-DD format
TODAY=$(date +%Y-%m-%d)

echo "Running voice diarization for location $LOCATION_ID on $TODAY"

# Run the main job
exec bash /app/scripts/start_voice_job.sh "$LOCATION_ID" "$TODAY"