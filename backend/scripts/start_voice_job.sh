#!/bin/bash
# Startup script for voice diarization job with compatibility fixes

set -e

echo "🚀 Starting Voice Diarization Job with compatibility fixes"
echo "================================"

# Export Python path
export PYTHONPATH=/app:$PYTHONPATH

# Test Pydantic compatibility first
echo "📋 Testing Pydantic compatibility..."
python /app/scripts/fix_pydantic_compat.py --test || {
    echo "⚠️ Pydantic compatibility test failed, but continuing..."
}

# Get parameters from command line args or environment variables
# Priority: command args > env vars
LOCATION_ID_PARAM=${1:-$LOCATION_ID}
DATE_PARAM=${2:-$DATE}

# Check if we have the required parameters
if [ -z "$LOCATION_ID_PARAM" ] || [ -z "$DATE_PARAM" ]; then
    echo "❌ Error: LOCATION_ID and DATE must be provided"
    echo ""
    echo "Usage:"
    echo "  Method 1 - Command arguments:"
    echo "    $0 <location_id> <date>"
    echo ""
    echo "  Method 2 - Environment variables:"
    echo "    Set LOCATION_ID and DATE env vars in Porter dashboard"
    echo ""
    echo "Current values:"
    echo "  LOCATION_ID (env): ${LOCATION_ID:-not set}"
    echo "  DATE (env): ${DATE:-not set}"
    echo "  Args: $@"
    exit 1
fi

echo "📍 Location ID: $LOCATION_ID_PARAM"
echo "📅 Date: $DATE_PARAM"

# Run the main job with compatibility fixes
echo ""
echo "🔄 Starting main job..."

# Use the lightweight database module if there are import issues
export USE_LIGHTWEIGHT_DB=1

# Run with explicit Python unbuffered output
# Pass remaining args after location_id and date
exec python -u /app/scripts/run_voice_diarization.py "$LOCATION_ID_PARAM" "$DATE_PARAM" "${@:3}"