#!/bin/bash

# Hoptix Sequential Runner
# Single-threaded video processing pipeline (like the original approach)

echo "🚀 Hoptix Sequential Video Processing Pipeline"
echo "=============================================="

# Validate required arguments
if [ $# -lt 3 ]; then
    echo "❌ Error: Organization ID, Location ID, and Date arguments required"
    echo "Usage: $0 ORG_ID LOCATION_ID YYYY-MM-DD"
    echo "Example: $0 abc123-def4-5678-90ab-cdef12345678 def456-789a-bcde-f012-3456789abcde 2025-08-29"
    echo ""
    echo "Note: This processes videos one at a time (sequential mode)."
    exit 1
fi

ORG_ID=$1
LOCATION_ID=$2
DATE_ARG=$3

echo "🏢 Organization ID: $ORG_ID"
echo "📍 Location ID: $LOCATION_ID"
echo "📅 Processing date: $DATE_ARG"
echo "🔄 Mode: Sequential (one video at a time)"

# Change to the hoptix-flask directory
cd "$(dirname "$0")/.."

# Create logs directory
mkdir -p logs

echo ""
echo "🚀 Starting sequential pipeline..."
echo ""

# Run the sequential processing using the full-pipeline command
python -c "
import sys
sys.path.insert(0, '.')
from commands.run_full_pipeline import FullPipelineCommand
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sequential_pipeline.log'),
        logging.StreamHandler()
    ]
)

# Run the full pipeline
command = FullPipelineCommand()
try:
    command.run('$ORG_ID', '$LOCATION_ID', '$DATE_ARG')
    print('✅ Sequential pipeline completed successfully!')
except Exception as e:
    print(f'❌ Sequential pipeline failed: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "📊 Final Summary:"
    echo "=================="
    
    # Get final status counts
    python -c "
from integrations.db_supabase import Supa
from config import Settings
import os
from dotenv import load_dotenv

load_dotenv()
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# Get status counts for this location
ready_result = db.client.table('videos').select('id', count='exact').eq('location_id', '$LOCATION_ID').eq('status', 'ready').execute()
failed_result = db.client.table('videos').select('id', count='exact').eq('location_id', '$LOCATION_ID').eq('status', 'failed').execute()
processing_result = db.client.table('videos').select('id', count='exact').eq('location_id', '$LOCATION_ID').eq('status', 'processing').execute()

print(f'✅ Successfully processed: {ready_result.count}')
print(f'❌ Failed: {failed_result.count}') 
print(f'🔄 Still processing: {processing_result.count}')
"
    
    echo ""
    echo "✅ Sequential pipeline completed!"
    echo "📁 Pipeline log available at: logs/sequential_pipeline.log"
else
    echo ""
    echo "❌ Sequential pipeline failed!"
    exit 1
fi
