#!/bin/bash

# Hoptix Production Runner - Parallel Version
# Parallel media processing pipeline with configurable workers (video and audio)

echo "🚀 Hoptix Parallel Media Processing Pipeline"
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

# Step 1: Import media files from Google Drive (using import service directly)
echo ""
echo "📥 Step 1: Importing media files from Google Drive..."
RUN_ID=$(python3 -c "
import sys
import logging
sys.path.insert(0, '.')

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from config import Settings
from services.import_service import ImportService
from dotenv import load_dotenv

try:
    load_dotenv()
    settings = Settings()
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    s3 = get_s3(settings.AWS_REGION)

    print('🔧 Getting folder name from location...', file=sys.stderr)
    # Get folder_name from location_id
    folder_name = db.client.table(\"locations\").select(\"name\").eq(\"id\", \"$LOCATION_ID\").limit(1).execute().data[0][\"name\"]
    print(f'📁 Using folder name: {folder_name}', file=sys.stderr)

    print('🔧 Initializing import service...', file=sys.stderr)
    import_service = ImportService(db, settings, folder_name)
    
    print('📥 Starting Google Drive import...', file=sys.stderr)
    imported_video_ids = import_service.import_videos_from_gdrive(s3, \"$ORG_ID\", \"$LOCATION_ID\", \"$DATE_ARG\")
    
    print(f'✅ Successfully imported {len(imported_video_ids)} videos', file=sys.stderr)
    if imported_video_ids:
        print('📋 Imported video IDs:', ', '.join(imported_video_ids), file=sys.stderr)
    
    # Get the run_id from one of the imported videos
    if imported_video_ids:
        print('🔍 Getting run_id from imported video...', file=sys.stderr)
        result = db.client.table('videos').select('run_id').eq('id', imported_video_ids[0]).limit(1).execute()
        if result.data:
            run_id = result.data[0]['run_id']
            print(f'🆔 Found run_id: {run_id}', file=sys.stderr)
            print(run_id)  # Print run_id to stdout for capture
        else:
            print('❌ Could not find run_id for imported video', file=sys.stderr)
            sys.exit(1)
    else:
        print('❌ No videos imported', file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Import failed: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
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

# Step 2: Check for large WAV files and split them if needed
echo ""
echo "🔍 Step 2: Checking for large WAV files that need splitting..."
python3 -c "
import sys
import logging
sys.path.insert(0, '.')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from config import Settings
from services.wav_splitter import WAVSplitter
from integrations.gdrive_client import GoogleDriveClient
import tempfile
import os
from dotenv import load_dotenv

try:
    load_dotenv()
    settings = Settings()
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    s3 = get_s3(settings.AWS_REGION)

    run_id = '$RUN_ID'
    print(f'🔍 Checking for large WAV files in run: {run_id}', file=sys.stderr)
    
    # Get all uploaded videos for this run
    result = db.client.table('videos').select('*').eq('run_id', run_id).eq('status', 'uploaded').execute()
    print(f'📊 Found {len(result.data)} uploaded videos to check', file=sys.stderr)
    
    wav_splitter = WAVSplitter(db, settings)
    gdrive = GoogleDriveClient()
    
    for video in result.data:
        video_id = video['id']
        s3_key = video.get('s3_key', '')
        meta = video.get('meta', {})
        gdrive_file_id = meta.get('gdrive_file_id')
        file_name = meta.get('gdrive_file_name', 'Unknown')
        
        # Check if this is a WAV file
        if not s3_key.lower().endswith('.wav'):
            print(f'⏭️ Skipping non-WAV file: {file_name}', file=sys.stderr)
            continue
            
        print(f'🎵 Checking WAV file: {file_name}', file=sys.stderr)
        
        # Download the file temporarily to check if it needs splitting
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_wav_path = tmp_file.name
            
        try:
            if gdrive.download_file(gdrive_file_id, tmp_wav_path):
                should_split, reason = wav_splitter.should_split_wav(tmp_wav_path)
                
                if should_split:
                    print(f'🔪 Large WAV detected: {reason}', file=sys.stderr)
                    print(f'📏 Splitting {file_name} into chunks...', file=sys.stderr)
                    
                    # Split the WAV file and create chunk video records
                    chunk_records = wav_splitter.process_large_wav_file(tmp_wav_path, video)
                    
                    if chunk_records:
                        print(f'✅ Successfully split into {len(chunk_records)} chunks', file=sys.stderr)
                        # Mark original video as processed (since it's now split into chunks)
                        db.client.table('videos').update({'status': 'ready'}).eq('id', video_id).execute()
                        print(f'📝 Marked original video {video_id} as ready (split into chunks)', file=sys.stderr)
                        
                        # Store chunk file paths in a way that workers can access them
                        # We'll store them in the meta field of each chunk record
                        for chunk_record in chunk_records:
                            chunk_id = chunk_record['id']
                            chunk_path = chunk_record['meta']['local_chunk_path']
                            # Update the chunk record to include the local path for processing
                            db.client.table('videos').update({
                                'meta': chunk_record['meta']
                            }).eq('id', chunk_id).execute()
                            print(f'💾 Stored chunk path for {chunk_id}: {chunk_path}', file=sys.stderr)
                    else:
                        print(f'❌ Failed to split WAV file {file_name}', file=sys.stderr)
                else:
                    print(f'✅ WAV file is within limits: {reason}', file=sys.stderr)
                    # For non-split files, we can remove the temporary file
                    os.remove(tmp_wav_path)
            else:
                print(f'❌ Failed to download WAV file for checking: {file_name}', file=sys.stderr)
                
        except Exception as e:
            print(f'❌ Error checking WAV file {file_name}: {e}', file=sys.stderr)
        finally:
            # Only clean up if the file wasn't split (split files keep their temp files)
            if os.path.exists(tmp_wav_path):
                # Check if this file was split by looking for chunk records
                chunk_check = db.client.table('videos').select('id').eq('run_id', run_id).contains('meta', {'original_video_id': video_id}).execute()
                if not chunk_check.data:
                    # No chunks found, so this file wasn't split, safe to delete
                    os.remove(tmp_wav_path)
                    print(f'🗑️ Cleaned up temporary file: {tmp_wav_path}', file=sys.stderr)
                
    print('✅ WAV file splitting check completed', file=sys.stderr)
    
except Exception as e:
    print(f'❌ WAV splitting check failed: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ WAV splitting check failed, exiting..."
    exit 1
fi

# Step 3: Get list of media files to process (including any new chunks)
echo ""
echo "📋 Step 3: Getting list of media files to process..."
MEDIA_FILES=$(python3 -c "
from integrations.db_supabase import Supa
from config import Settings
import os
import sys
from dotenv import load_dotenv

load_dotenv()
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

run_id = '$RUN_ID'
print(f'🔍 Looking for videos with run_id: {run_id}', file=sys.stderr)

# Get all media files for this run_id first to see their status
all_result = db.client.table('videos').select('id, status, meta').eq('run_id', run_id).execute()
print(f'📊 Found {len(all_result.data)} total videos in database:', file=sys.stderr)
for video in all_result.data:
    meta = video.get('meta', {})
    is_chunk = meta.get('is_chunk', False)
    chunk_info = f' (chunk {meta.get(\"chunk_number\", \"?\")}/{meta.get(\"total_chunks\", \"?\")})' if is_chunk else ''
    print(f'  - ID: {video[\"id\"]}, Status: {video[\"status\"]}{chunk_info}', file=sys.stderr)

# Get uploaded media files for this run_id (including chunks)
result = db.client.table('videos').select('id').eq('run_id', run_id).eq('status', 'uploaded').execute()
print(f'✅ Found {len(result.data)} uploaded videos ready for processing', file=sys.stderr)

media_ids = [media['id'] for media in result.data]
print(' '.join(media_ids))
")

if [ -z "$MEDIA_FILES" ]; then
    echo "ℹ️ No media files found to process"
    exit 0
fi

MEDIA_ARRAY=($MEDIA_FILES)
TOTAL_MEDIA=${#MEDIA_ARRAY[@]}

echo "📊 Found $TOTAL_MEDIA media files to process"
echo "🚀 Starting $NUM_WORKERS parallel workers..."
echo ""

# Step 4: Process media files in parallel
PIDS=()
WORKER_COUNT=0

for media_id in "${MEDIA_ARRAY[@]}"; do
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
    echo "🔄 Worker $WORKER_COUNT: Starting media $media_id"
    
    # Process media file in background
    (
        python3 -c "
import sys
import logging
from datetime import datetime
sys.path.insert(0, '.')

# Set up detailed logging for this worker
worker_id = $WORKER_COUNT
logging.basicConfig(
    level=logging.INFO, 
    format=f'[Worker {worker_id}] %(levelname)s: %(message)s',
    stream=sys.stderr
)

from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from config import Settings
from worker.pipeline import claim_video, mark_status
from services.processing_service import ProcessingService
from integrations.gdrive_client import GoogleDriveClient
import tempfile
import os
from dotenv import load_dotenv

try:
    load_dotenv()
    settings = Settings()
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    s3 = get_s3(settings.AWS_REGION)

    media_id = '$media_id'
    start_time = datetime.now()
    print(f'🚀 [Worker {worker_id}] Starting processing at {start_time.strftime(\"%H:%M:%S\")}')
    print(f'📋 [Worker {worker_id}] Processing media: {media_id}')

    # Claim media file
    print(f'🔒 [Worker {worker_id}] Attempting to claim media {media_id}...')
    if not claim_video(db, media_id):
        print(f'❌ [Worker {worker_id}] Could not claim media {media_id} - may be already claimed')
        sys.exit(1)
    print(f'✅ [Worker {worker_id}] Successfully claimed media {media_id}')
    
    # Get media details
    print(f'📋 [Worker {worker_id}] Fetching media details from database...')
    result = db.client.table('videos').select('id, s3_key, run_id, location_id, started_at, ended_at, meta').eq('id', media_id).limit(1).execute()
    if not result.data:
        print(f'❌ [Worker {worker_id}] Media {media_id} not found in database')
        sys.exit(1)
    
    row = result.data[0]
    meta = row.get('meta', {})
    s3_key = row['s3_key']
    file_name = meta.get('gdrive_file_name', 'Unknown')
    
    # Check if this is a WAV chunk (has local file path)
    is_wav_chunk = meta.get('is_chunk', False) and meta.get('local_chunk_path')
    
    print(f'📁 [Worker {worker_id}] Media details:')
    print(f'   📄 File: {file_name}')
    if is_wav_chunk:
        print(f'   🎵 WAV Chunk: {meta.get(\"chunk_number\", \"?\")}/{meta.get(\"total_chunks\", \"?\")}')
        print(f'   📍 Local path: {meta.get(\"local_chunk_path\")}')
    else:
        gdrive_file_id = meta.get('gdrive_file_id')
        print(f'   🆔 GDrive ID: {gdrive_file_id}')
    print(f'   🗂️ S3 Key: {s3_key}')
    
    # Determine file extension from S3 key
    import os
    file_ext = os.path.splitext(s3_key)[1] or '.mp4'
    print(f'📎 [Worker {worker_id}] File extension: {file_ext}')
    
    # Handle WAV chunks vs regular files
    if is_wav_chunk:
        # For WAV chunks, use the local file path directly
        tmp_media_path = meta.get('local_chunk_path')
        if not tmp_media_path or not os.path.exists(tmp_media_path):
            print(f'❌ [Worker {worker_id}] WAV chunk file not found: {tmp_media_path}')
            mark_status(db, media_id, 'failed')
            sys.exit(1)
        
        print(f'🎵 [Worker {worker_id}] Using local WAV chunk file: {tmp_media_path}')
        file_size = os.path.getsize(tmp_media_path)
        print(f'📏 [Worker {worker_id}] Chunk size: {file_size:,} bytes')
        
        # Process the WAV chunk directly
        print(f'🔧 [Worker {worker_id}] Initializing processing service...')
        processing_service = ProcessingService(db, settings)
        
        processing_start = datetime.now()
        print(f'🎵 [Worker {worker_id}] Starting WAV chunk processing pipeline...')
        processing_service.process_wav_from_local_file(row, tmp_media_path)
        
        processing_time = (datetime.now() - processing_start).total_seconds()
        print(f'✅ [Worker {worker_id}] WAV chunk processing completed in {processing_time:.1f}s')
        mark_status(db, media_id, 'ready')
        
        total_time = (datetime.now() - start_time).total_seconds()
        print(f'🎉 [Worker {worker_id}] Successfully processed WAV chunk {media_id} in {total_time:.1f}s total')
        
        # Clean up the chunk file after processing
        print(f'🧹 [Worker {worker_id}] Cleaning up WAV chunk file...')
        try:
            os.remove(tmp_media_path)
            print(f'🗑️ [Worker {worker_id}] Removed WAV chunk file: {tmp_media_path}')
        except Exception as cleanup_error:
            print(f'⚠️ [Worker {worker_id}] Could not clean up chunk file: {cleanup_error}')
            
    else:
        # For regular files, download from Google Drive
        gdrive_file_id = meta.get('gdrive_file_id')
        print(f'📥 [Worker {worker_id}] Initializing Google Drive client...')
        gdrive = GoogleDriveClient()
        
        print(f'📁 [Worker {worker_id}] Creating temporary file for download...')
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
            tmp_media_path = tmp_file.name
        
        print(f'💾 [Worker {worker_id}] Temporary file: {tmp_media_path}')
        
        try:
            print(f'⬇️ [Worker {worker_id}] Downloading file from Google Drive...')
            download_start = datetime.now()
            
            if gdrive.download_file(gdrive_file_id, tmp_media_path):
                download_time = (datetime.now() - download_start).total_seconds()
                file_size = os.path.getsize(tmp_media_path)
                print(f'✅ [Worker {worker_id}] Download completed in {download_time:.1f}s ({file_size:,} bytes)')
                
                print(f'🔧 [Worker {worker_id}] Initializing processing service...')
                processing_service = ProcessingService(db, settings)
                
                processing_start = datetime.now()
                if file_ext.lower() in ['.wav', '.mp3', '.m4a', '.aac', '.ogg', '.flac']:
                    print(f'🎵 [Worker {worker_id}] Starting WAV/audio processing pipeline...')
                    processing_service.process_wav_from_local_file(row, tmp_media_path)
                else:
                    # Process as video file (including MKV files) - use the full pipeline with clips
                    print(f'🎬 [Worker {worker_id}] Starting video processing pipeline...')
                    # Use the method that includes stages 7-8 (clips)
                    processing_service.process_video_from_local_file_with_clips(row, tmp_media_path)
                
                processing_time = (datetime.now() - processing_start).total_seconds()
                
                print(f'✅ [Worker {worker_id}] Video processing completed in {processing_time:.1f}s')
                mark_status(db, media_id, 'ready')
                
                total_time = (datetime.now() - start_time).total_seconds()
                print(f'🎉 [Worker {worker_id}] Successfully processed media {media_id} in {total_time:.1f}s total')
            else:
                print(f'❌ [Worker {worker_id}] Failed to download media {media_id} from Google Drive')
                mark_status(db, media_id, 'failed')
                sys.exit(1)
        except Exception as processing_error:
            print(f'❌ [Worker {worker_id}] Error during processing: {processing_error}')
            import traceback
            traceback.print_exc(file=sys.stderr)
            mark_status(db, media_id, 'failed')
            sys.exit(1)
        finally:
            print(f'🧹 [Worker {worker_id}] Cleaning up temporary files...')
            if os.path.exists(tmp_media_path):
                os.remove(tmp_media_path)
                print(f'🗑️ [Worker {worker_id}] Removed temporary file: {tmp_media_path}')
            
except Exception as e:
    print(f'❌ [Worker {worker_id}] Fatal error processing media {media_id}: {e}')
    import traceback
    traceback.print_exc(file=sys.stderr)
    try:
        mark_status(db, media_id, 'failed')
    except:
        pass
    sys.exit(1)
"
    ) &
    
    PIDS+=($!)
done

echo ""
echo "⏳ Waiting for all workers to complete..."

# Wait for all background processes to complete with progress tracking
completed_workers=0
total_workers=${#PIDS[@]}
echo "📊 Monitoring $total_workers workers..."

for pid in "${PIDS[@]}"; do
    wait $pid
    completed_workers=$((completed_workers + 1))
    echo "✅ Worker $completed_workers/$total_workers completed"
done

echo ""
echo "📊 Processing Summary:"
echo "=============================="

# Get final status counts with detailed breakdown
python3 -c "
from integrations.db_supabase import Supa
from config import Settings
import os
from dotenv import load_dotenv

load_dotenv()
settings = Settings()
db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

run_id = '$RUN_ID'
print(f'🔍 Final status check for run: {run_id}')

# Get all videos for this run with their status
all_videos = db.client.table('videos').select('id, status, meta').eq('run_id', run_id).execute()
print(f'📊 Total videos in run: {len(all_videos.data)}')

# Get status counts for this run
ready_result = db.client.table('videos').select('id', count='exact').eq('run_id', run_id).eq('status', 'ready').execute()
failed_result = db.client.table('videos').select('id', count='exact').eq('run_id', run_id).eq('status', 'failed').execute()
processing_result = db.client.table('videos').select('id', count='exact').eq('run_id', run_id).eq('status', 'processing').execute()
uploaded_result = db.client.table('videos').select('id', count='exact').eq('run_id', run_id).eq('status', 'uploaded').execute()

print(f'✅ Successfully processed: {ready_result.count}')
print(f'❌ Failed: {failed_result.count}') 
print(f'🔄 Still processing: {processing_result.count}')
print(f'📥 Still uploaded (not processed): {uploaded_result.count}')

# Show details of failed videos if any
if failed_result.count > 0:
    print(f'\\n❌ Failed video details:')
    failed_videos = db.client.table('videos').select('id, meta').eq('run_id', run_id).eq('status', 'failed').execute()
    for video in failed_videos.data:
        file_name = video['meta'].get('gdrive_file_name', 'Unknown') if video['meta'] else 'Unknown'
        print(f'   - {video[\"id\"]}: {file_name}')
"

# Step 5: Run Analytics on processed transactions
echo ""
echo "📊 Step 5: Running analytics on processed transactions..."
python3 -c "
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