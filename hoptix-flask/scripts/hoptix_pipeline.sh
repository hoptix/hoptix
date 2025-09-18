#!/bin/bash

# Hoptix Production Runner - Parallel Version
# Parallel video processing pipeline with configurable workers

echo "🚀 Hoptix Parallel Video Processing Pipeline"
echo "============================================="

# Validate required arguments
if [ $# -lt 2 ]; then
    echo "❌ Error: Organization ID and Location ID arguments required"
    echo "Usage: $0 ORG_ID LOCATION_ID [YYYY-MM-DD] [NUM_WORKERS]"
    echo "Example: $0 abc123-def4-5678-90ab-cdef12345678 def456-789a-bcde-f012-3456789abcde 2025-08-29 11"
    echo ""
    echo "Note: This script is designed for single-tenant restaurant deployments."
    echo "The organization and location must already exist in the database."
    echo "If no date is provided, today's date in Pacific Time will be used."
    exit 1
fi

ORG_ID=$1
LOCATION_ID=$2
# Default to today's date in Pacific Time if not provided
DATE_ARG=${3:-$(TZ=America/Los_Angeles date +%Y-%m-%d)}
NUM_WORKERS=${4:-11}  # Default to 11 workers

echo "🏢 Organization ID: $ORG_ID"
echo "📍 Location ID: $LOCATION_ID"
echo "📅 Processing date: $DATE_ARG" 
echo "👥 Number of workers: $NUM_WORKERS"

# Change to the hoptix-flask directory
cd "$(dirname "$0")/.."

# Step 1: Import videos from Google Drive (using import service directly)
echo ""
echo "📥 Step 1: Importing videos from Google Drive..."
RUN_ID=$(python -c "
import sys
sys.path.insert(0, '.')
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from config import Settings
from services.import_service import ImportService
from dotenv import load_dotenv

load_dotenv()
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
s3 = get_s3(settings.AWS_REGION)

import_service = ImportService(db, settings)
try:
    imported_video_ids = import_service.import_videos_from_gdrive(s3, '$ORG_ID', '$LOCATION_ID', '$DATE_ARG')
    print(f'Successfully imported {len(imported_video_ids)} videos', file=sys.stderr)
    if imported_video_ids:
        print('Imported video IDs:', ', '.join(imported_video_ids), file=sys.stderr)
    
    # Get the run_id from one of the imported videos
    if imported_video_ids:
        result = db.client.table('videos').select('run_id').eq('id', imported_video_ids[0]).limit(1).execute()
        if result.data:
            print(result.data[0]['run_id'])  # Print run_id to stdout for capture
        else:
            print('', file=sys.stderr)  # Empty run_id
            sys.exit(1)
    else:
        print('', file=sys.stderr)  # No videos imported
        
except Exception as e:
    print(f'Import failed: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ $? -ne 0 ]; then
    echo "❌ Import failed, exiting..."
    exit 1
fi

if [ -z "$RUN_ID" ]; then
    echo "❌ No run ID found, exiting..."
    exit 1
fi

echo "🔄 Run ID: $RUN_ID"

# Step 2: Get list of videos to process
echo ""
echo "📋 Step 2: Getting list of videos to process..."
VIDEOS=$(python -c "
from integrations.db_supabase import Supa
from config import Settings
import os
from dotenv import load_dotenv

load_dotenv()
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# Get uploaded videos for this run_id
result = db.client.table('videos').select('id').eq('run_id', '$RUN_ID').eq('status', 'uploaded').execute()

video_ids = [video['id'] for video in result.data]
print(' '.join(video_ids))
")

if [ -z "$VIDEOS" ]; then
    echo "ℹ️ No videos found to process"
    exit 0
fi

VIDEO_ARRAY=($VIDEOS)
TOTAL_VIDEOS=${#VIDEO_ARRAY[@]}

echo "📊 Found $TOTAL_VIDEOS videos to process"
echo "🚀 Starting $NUM_WORKERS parallel workers..."
echo ""

# Step 3: Process videos in parallel
PIDS=()
WORKER_COUNT=0

for video_id in "${VIDEO_ARRAY[@]}"; do
    # Wait if we've reached max workers
    while [ ${#PIDS[@]} -ge $NUM_WORKERS ]; do
        # Check for completed processes
        for i in "${!PIDS[@]}"; do
            if ! kill -0 "${PIDS[i]}" 2>/dev/null; then
                # Process completed, remove from array
                unset "PIDS[i]"
                PIDS=("${PIDS[@]}")  # Reindex array
                break
            fi
        done
        sleep 1
    done
    
    # Start new worker
    WORKER_COUNT=$((WORKER_COUNT + 1))
    echo "🔄 Worker $WORKER_COUNT: Starting video $video_id"
    
    # Process video in background
    (
        python -c "
import sys
sys.path.insert(0, '.')
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from config import Settings
from worker.pipeline import claim_video, mark_status, process_one_video
from services.processing_service import ProcessingService
from integrations.gdrive_client import GoogleDriveClient
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
s3 = get_s3(settings.AWS_REGION)

video_id = '$video_id'
print(f'Worker processing video: {video_id}')

try:
    # Claim video
    if not claim_video(db, video_id):
        print(f'Could not claim video {video_id}')
        sys.exit(1)
    
    # Get video details
    result = db.client.table('videos').select('id, s3_key, run_id, location_id, started_at, ended_at, meta').eq('id', video_id).limit(1).execute()
    if not result.data:
        print(f'Video {video_id} not found')
        sys.exit(1)
    
    row = result.data[0]
    gdrive_file_id = row['meta']['gdrive_file_id']
    
    # Download from Google Drive and process
    gdrive = GoogleDriveClient()
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
        tmp_video_path = tmp_file.name
    
    try:
        if gdrive.download_file(gdrive_file_id, tmp_video_path):
            processing_service = ProcessingService(db, settings)
            processing_service.process_video_from_local_file(row, tmp_video_path)
            mark_status(db, video_id, 'ready')
            print(f'✅ Successfully processed video {video_id}')
        else:
            print(f'❌ Failed to download video {video_id}')
            mark_status(db, video_id, 'failed')
            sys.exit(1)
    finally:
        if os.path.exists(tmp_video_path):
            os.remove(tmp_video_path)
            
except Exception as e:
    print(f'❌ Error processing video {video_id}: {e}')
    mark_status(db, video_id, 'failed')
    sys.exit(1)
"
    ) &
    
    PIDS+=($!)
done

echo ""
echo "⏳ Waiting for all workers to complete..."

# Wait for all background processes to complete
for pid in "${PIDS[@]}"; do
    wait $pid
done

echo ""
echo "📊 Processing Summary:"
echo "=============================="

# Get final status counts
python -c "
from integrations.db_supabase import Supa
from config import Settings
import os
from dotenv import load_dotenv

load_dotenv()
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

# Get status counts for this run
ready_result = db.client.table('videos').select('id', count='exact').eq('run_id', '$RUN_ID').eq('status', 'ready').execute()
failed_result = db.client.table('videos').select('id', count='exact').eq('run_id', '$RUN_ID').eq('status', 'failed').execute()
processing_result = db.client.table('videos').select('id', count='exact').eq('run_id', '$RUN_ID').eq('status', 'processing').execute()

print(f'✅ Successfully processed: {ready_result.count}')
print(f'❌ Failed: {failed_result.count}') 
print(f'🔄 Still processing: {processing_result.count}')
"

# Step 4: Run Analytics on processed transactions
echo ""
echo "📊 Step 4: Running analytics on processed transactions..."
python -c "
import sys
sys.path.insert(0, '.')
from integrations.db_supabase import Supa
from config import Settings
from services.analytics_service import HoptixAnalyticsService
from services.analytics_storage_service import AnalyticsStorageService
from dotenv import load_dotenv
import json

load_dotenv()
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

try:
    # Query graded_rows_filtered view for this run_id
    result = db.client.from_('graded_rows_filtered').select('*').eq('run_id', '$RUN_ID').execute()
    
    if not result.data:
        print('ℹ️ No graded transactions found for this run')
        sys.exit(0)
    
    print(f'📋 Found {len(result.data)} graded transactions for analysis')
    
    # Initialize analytics services and generate report
    analytics_service = HoptixAnalyticsService()
    storage_service = AnalyticsStorageService(db)
    report = analytics_service.generate_comprehensive_report(result.data)
    
    # Display key metrics
    print('')
    print('📊 RUN ANALYTICS SUMMARY')
    print('=' * 40)
    summary = report['summary']
    print(f'Total Transactions: {summary[\"total_transactions\"]}')
    print(f'Complete Transactions: {summary[\"complete_transactions\"]}')
    print(f'Completion Rate: {summary[\"completion_rate\"]:.1f}%')
    
    # Upselling summary
    upselling = report['upselling']
    print(f'\\n🎯 Upselling: {upselling[\"total_successes\"]}/{upselling[\"total_opportunities\"]} ({upselling[\"conversion_rate\"]:.1f}%) - \${upselling.get(\"total_revenue\", 0):.2f}')
    
    # Upsizing summary  
    upsizing = report['upsizing']
    print(f'📏 Upsizing: {upsizing[\"total_successes\"]}/{upsizing[\"total_opportunities\"]} ({upsizing[\"conversion_rate\"]:.1f}%) - \${upsizing.get(\"total_revenue\", 0):.2f}')
    
    # Add-ons summary
    addons = report['addons']
    print(f'🍟 Add-ons: {addons[\"total_successes\"]}/{addons[\"total_opportunities\"]} ({addons[\"conversion_rate\"]:.1f}%) - \${addons.get(\"total_revenue\", 0):.2f}')
    
    # Operator performance (if available)
    operator_analytics = report.get('operator_analytics', {})
    if operator_analytics.get('upselling'):
        print('\\n👥 Top Performing Operators:')
        upselling_by_op = operator_analytics['upselling']
        sorted_operators = sorted(upselling_by_op.items(), key=lambda x: x[1]['conversion_rate'], reverse=True)[:3]
        for operator, metrics in sorted_operators:
            if metrics['total_opportunities'] > 0:
                print(f'  • {operator}: {metrics[\"conversion_rate\"]:.1f}% conversion, \${metrics.get(\"total_revenue\", 0):.2f} revenue')
    
    # Store analytics in database
    print('\\n💾 Storing analytics in database...')
    if storage_service.store_run_analytics('$RUN_ID', report):
        print('✅ Analytics successfully stored in database')
    else:
        print('❌ Failed to store analytics in database')
    
    # Also save detailed report as JSON file for backup
    report_filename = f'analytics_report_run_{\"$RUN_ID\"}.json'
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)
    print(f'💾 Detailed analytics also saved to {report_filename}')
    
except Exception as e:
    print(f'❌ Analytics failed: {e}')
    # Don't exit with error - analytics failure shouldn't fail the entire pipeline
"

echo ""
echo "✅ Parallel pipeline completed!"