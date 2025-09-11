#!/bin/bash

# Hoptix Production Runner
# Single script to run the full video processing pipeline for a restaurant instance

echo "🚀 Hoptix Video Processing Pipeline"
echo "===================================="

# Validate required arguments
if [ $# -lt 3 ]; then
    echo "❌ Error: Organization ID, Location ID, and Date arguments required"
    echo "Usage: $0 ORG_ID LOCATION_ID YYYY-MM-DD"
    echo "Example: $0 abc123-def4-5678-90ab-cdef12345678 def456-789a-bcde-f012-3456789abcde 2025-08-29"
    echo ""
    echo "Note: This script is designed for single-tenant restaurant deployments."
    echo "The organization and location must already exist in the database."
    exit 1
fi

ORG_ID=$1
LOCATION_ID=$2
DATE_ARG=$3

echo "🏢 Organization ID: $ORG_ID"
echo "📍 Location ID: $LOCATION_ID"
echo "📅 Processing date: $DATE_ARG"

# Change to the hoptix-flask directory
cd "$(dirname "$0")/.."

# Run the full pipeline using the new modular structure
echo "🔄 Starting full pipeline (import + process)..."
python scripts/hoptix_runner.py full-pipeline --org-id "$ORG_ID" --location-id "$LOCATION_ID" --date "$DATE_ARG"

echo "✅ Pipeline completed!"
