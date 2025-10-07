#!/usr/bin/env python3
"""
Process a WAV file from local downloads folder through the full pipeline
Usage: python process_local_wav.py <filename> <org_id> <location_id> <date>
Example: python process_local_wav.py "DQ Cary_20251002-20251002_1000.wav" org123 loc456 2025-01-02
"""

import os
import sys
import uuid
import tempfile
import logging
import shutil
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from integrations.gdrive_client import GoogleDriveClient
from config import Settings
from services.database_service import DatabaseService
from services.processing_service import ProcessingService
from services.wav_splitter import WAVSplitter
from worker.adapter import transcribe_video, split_into_transactions, grade_transactions
import subprocess
import tempfile
from dateutil import parser as dtparser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_wav_duration_seconds(wav_path: str) -> float:
    """Get WAV file duration in seconds using ffprobe"""
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1",
            wav_path
        ])
        return float(out.decode().strip())
    except Exception as e:
        logger.error(f"Failed to get WAV duration: {e}")
        return 0.0

def ffmpeg_cut(wav_path: str, out_path: str, start_sec: float, end_sec: float) -> None:
    """Cut audio clip using ffmpeg"""
    duration = max(0.0, end_sec - start_sec)
    if duration <= 0.0:
        return
    cmd = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-ss", f"{start_sec:.3f}",
        "-i", wav_path,
        "-t", f"{duration:.3f}",
        "-c", "copy",  # fast for WAV
        out_path,
    ]
    subprocess.run(cmd, check=True)

def upload_clip_to_gdrive(local_path: str, folder_name: str, filename: str) -> str:
    """Upload audio clip to Google Drive and return shareable link"""
    try:
        gdrive = GoogleDriveClient()
        file_id = gdrive.upload_file(local_path, folder_name, filename)
        if file_id:
            return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        return None
    except Exception as e:
        logger.error(f"Error uploading clip to Google Drive: {e}")
        return None

def process_transaction_clips(run_id: str, original_wav_path: str, run_date: str, db) -> int:
    """Process transaction audio clips and upload to Google Drive"""
    logger.info("🎵 Processing transaction audio clips...")
    
    # Create folder name with date in MM-DD format
    try:
        # Parse run_date (YYYY-MM-DD) and convert to MM-DD
        date_obj = datetime.strptime(run_date, "%Y-%m-%d")
        folder_date = date_obj.strftime("%m-%d")
    except:
        folder_date = "unknown"
    
    clips_folder_name = f"Clips_{folder_date}"
    logger.info(f"🗂️ Using Google Drive folder: {clips_folder_name}")
    
    # Get all transactions for this run
    try:
        result = db.client.table("transactions").select("id, started_at, ended_at, video_id").eq("run_id", run_id).execute()
        transactions = result.data or []
        logger.info(f"📋 Found {len(transactions)} transactions to process")
    except Exception as e:
        logger.error(f"Failed to fetch transactions: {e}")
        return 0
    
    if not transactions:
        logger.info("No transactions found to process")
        return 0
    
    # Get WAV duration for bounds checking
    wav_duration = get_wav_duration_seconds(original_wav_path)
    logger.info(f"⏱️ Original WAV duration: {wav_duration:.1f} seconds")
    
    # Process clips in temporary directory
    clips_processed = 0
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"📁 Using temporary directory: {temp_dir}")
        
        for tx in transactions:
            tx_id = tx["id"]
            video_id = tx.get("video_id")
            
            try:
                # Parse transaction times
                if not tx.get("started_at") or not tx.get("ended_at"):
                    logger.warning(f"⚠️ Skipping transaction {tx_id}: missing timestamps")
                    continue
                
                tx_start = dtparser.isoparse(tx["started_at"])
                tx_end = dtparser.isoparse(tx["ended_at"])
                
                # For chunked videos, we need to map to the original WAV timeline
                # Get video metadata to understand chunk timing
                if video_id:
                    video_result = db.client.table("videos").select("meta, started_at").eq("id", video_id).limit(1).execute()
                    if video_result.data:
                        video_meta = video_result.data[0].get("meta", {})
                        video_start = dtparser.isoparse(video_result.data[0]["started_at"])
                        
                        # If this is a chunk, adjust timestamps relative to original WAV
                        if video_meta.get("is_chunk"):
                            chunk_start_time = video_meta.get("chunk_start_time", 0)
                            # Adjust transaction times to be relative to original WAV
                            tx_start_sec = (tx_start - video_start).total_seconds() + chunk_start_time
                            tx_end_sec = (tx_end - video_start).total_seconds() + chunk_start_time
                        else:
                            # For non-chunked videos, use relative timing
                            tx_start_sec = (tx_start - video_start).total_seconds()
                            tx_end_sec = (tx_end - video_start).total_seconds()
                    else:
                        logger.warning(f"⚠️ Could not find video metadata for {video_id}")
                        continue
                else:
                    logger.warning(f"⚠️ No video_id for transaction {tx_id}")
                    continue
                
                # Clamp to WAV bounds
                start_sec = max(0.0, min(tx_start_sec, wav_duration))
                end_sec = max(0.0, min(tx_end_sec, wav_duration))
                
                # Skip if duration is too short
                if end_sec - start_sec < 0.5:
                    logger.warning(f"⚠️ Skipping {tx_id}: duration too short ({end_sec - start_sec:.3f}s)")
                    continue
                
                # Create clip filename
                clip_filename = f"tx_{tx_id}.wav"
                clip_path = os.path.join(temp_dir, clip_filename)
                
                # Cut the audio clip
                ffmpeg_cut(original_wav_path, clip_path, start_sec, end_sec)
                logger.info(f"✂️ Cut clip {tx_id}: {start_sec:.3f}s - {end_sec:.3f}s ({end_sec - start_sec:.3f}s)")
                
                # Upload to Google Drive
                clip_link = upload_clip_to_gdrive(clip_path, clips_folder_name, clip_filename)
                
                if clip_link:
                    # Update transaction with clip link
                    db.client.table("transactions").update({
                        "clip_s3_url": clip_link
                    }).eq("id", tx_id).execute()
                    
                    clips_processed += 1
                    logger.info(f"✅ Uploaded clip {tx_id}: {clip_link}")
                else:
                    logger.error(f"❌ Failed to upload clip for {tx_id}")
                
            except Exception as e:
                logger.error(f"❌ Error processing clip for transaction {tx_id}: {e}")
                continue
    
    logger.info(f"🎉 Processed {clips_processed} transaction audio clips")
    return clips_processed

def find_wav_file(filename: str, downloads_path: str = None) -> str:
    """Find the WAV file in downloads folder or specified path"""
    
    # Common downloads paths
    if downloads_path is None:
        possible_paths = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
            "/Users/ronitjain/Downloads",  # Specific to your setup
            "/Users/ronitjain/Desktop",    # Specific to your setup
        ]
    else:
        possible_paths = [downloads_path]
    
    # Try to find the file
    for path in possible_paths:
        if os.path.exists(path):
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path):
                logger.info(f"✅ Found WAV file: {full_path}")
                return full_path
                
            # Try with .wav extension if not provided
            if not filename.lower().endswith('.wav'):
                full_path = os.path.join(path, filename + '.wav')
                if os.path.exists(full_path):
                    logger.info(f"✅ Found WAV file: {full_path}")
                    return full_path
    
    # If not found, list available WAV files
    logger.error(f"❌ Could not find file: {filename}")
    logger.info("🔍 Searching for available WAV files...")
    
    for path in possible_paths:
        if os.path.exists(path):
            wav_files = [f for f in os.listdir(path) if f.lower().endswith('.wav')]
            if wav_files:
                logger.info(f"📁 WAV files in {path}:")
                for wav_file in wav_files[:10]:  # Show first 10
                    logger.info(f"   - {wav_file}")
                if len(wav_files) > 10:
                    logger.info(f"   ... and {len(wav_files) - 10} more")
    
    return None

def process_local_wav(filename: str, org_id: str, location_id: str, run_date: str, downloads_path: str = None):
    """Process a WAV file from local downloads folder through the full pipeline"""
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize services
        logger.info("🔧 Initializing services...")
        settings = Settings()
        db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        database_service = DatabaseService(db)
        processing_service = ProcessingService(db, settings)
        wav_splitter = WAVSplitter(db, settings)
        
        logger.info("✅ Services initialized successfully")
        
        # Find the WAV file
        logger.info(f"🔍 Looking for WAV file: {filename}")
        wav_path = find_wav_file(filename, downloads_path)
        
        if not wav_path:
            logger.error(f"❌ Could not find WAV file: {filename}")
            return None
        
        # Get file information
        file_name = os.path.basename(wav_path)
        file_size = os.path.getsize(wav_path)
        
        logger.info(f"📄 File name: {file_name}")
        logger.info(f"📊 File size: {file_size:,} bytes ({file_size / (1024*1024):.1f}MB)")
        logger.info(f"📍 File path: {wav_path}")
        
        # Check if file needs splitting
        should_split, reason = wav_splitter.should_split_wav(wav_path)
        logger.info(f"🔍 File analysis: {reason}")
        
        if should_split:
            logger.info(f"🔪 Large WAV file detected, splitting into chunks...")
            
            # Create run for the provided org and location
            logger.info("🔧 Creating run in database...")
            run_id = database_service.create_run_for_date(org_id, location_id, run_date)
            logger.info(f"✅ Created run with ID: {run_id}")
        

            # Parse date for started_at/ended_at
            try:
                run_datetime = datetime.strptime(run_date, "%Y-%m-%d")
                run_datetime = run_datetime.replace(tzinfo=timezone.utc)
                started_at = run_datetime
                ended_at = run_datetime + timedelta(hours=24)  # Assume full day
            except ValueError:
                logger.warning(f"Could not parse date {run_date}, using current time")
                started_at = datetime.now(timezone.utc)
                ended_at = started_at + timedelta(hours=24)

            #check if video record already exists 
            video_result = db.client.table("videos").select("id").eq("run_id", run_id).eq("location_id", location_id).eq("camera_id", f"local-wav-{file_name[:8]}").limit(1).execute()
            if video_result.data:
                video_id = video_result.data[0]["id"]
            else:
                video_id = str(uuid.uuid4())

            video_data = {
                "id": video_id,
                "run_id": run_id,
                "location_id": location_id,
                "camera_id": f"local-wav-{file_name[:8]}",
                "s3_key": f"local/wav_processing/{video_id}/{file_name}",  # Use video_id UUID for uniqueness
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "status": "uploaded",
                "meta": {
                    "source": "local_wav_file",
                    "local_file_path": wav_path,
                    "file_name": file_name,
                    "file_size": file_size,
                    "processing_type": "local_wav_processing",
                    "organization_id": org_id  # Store org_id in meta instead
                }
            }


            db.client.table("videos").upsert(video_data, on_conflict="id").execute()
            logger.info(f"✅ Created video record with ID: {video_id}")
        
            # Split the WAV file into chunks and create video records for each chunk
            logger.info("🔪 Splitting WAV file into chunks...")
            chunk_records = wav_splitter.process_large_wav_file(wav_path, video_data)
            
            if not chunk_records:
                logger.error("❌ Failed to split WAV file")
                return None
            
            logger.info(f"✅ Successfully split into {len(chunk_records)} chunks")
            
            # Mark original video as ready (since it's now split into chunks)
            db.client.table("videos").update({"status": "processing"}).eq("id", video_id).execute()
            logger.info("📝 Marked original video as ready (split into chunks)")
            
            # Process chunks in parallel - TRANSACTIONS FIRST
            total_transactions = 0
            
            logger.info("🎵 PHASE 1: Processing chunks for transactions (5 workers)...")
            
            def process_chunk_for_transactions(chunk_data):
                """Process a single chunk for transactions only"""
                i, chunk_record = chunk_data
                chunk_id = chunk_record["id"]
                chunk_path = chunk_record["meta"]["local_chunk_path"]
                chunk_meta = chunk_record["meta"]
                
                logger.info(f"🎵 Processing chunk {i}/{len(chunk_records)} for transactions: {chunk_id}")
                logger.info(f"   📍 Path: {chunk_path}")
                logger.info(f"   ⏱️ Time: {chunk_meta['chunk_start_time']:.1f}s - {chunk_meta['chunk_end_time']:.1f}s")
                
                try:
                    # Process the chunk (transactions only)
                    processing_service.process_wav_from_local_file(chunk_record, chunk_path)
                    
                    # Get transaction count for this chunk
                    tx_result = db.client.table("transactions").select("id", count="exact").eq("video_id", chunk_id).execute()
                    chunk_tx_count = tx_result.count
                    
                    logger.info(f"✅ Chunk {i} transactions processed: {chunk_tx_count} transactions")
                    return chunk_tx_count
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process chunk {i} for transactions: {e}")
                    import traceback
                    traceback.print_exc()
                    return 0
            
            # Process chunks in parallel with 5 workers
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all chunk processing tasks
                future_to_chunk = {
                    executor.submit(process_chunk_for_transactions, (i, chunk_record)): (i, chunk_record)
                    for i, chunk_record in enumerate(chunk_records, 1)
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_chunk):
                    i, chunk_record = future_to_chunk[future]
                    try:
                        chunk_tx_count = future.result()
                        total_transactions += chunk_tx_count
                    except Exception as e:
                        logger.error(f"❌ Chunk {i} processing failed: {e}")
            
            logger.info(f"🎉 PHASE 1 COMPLETE: {total_transactions} total transactions processed")
            
            # PHASE 2: Grade all transactions in parallel
            logger.info("🎯 PHASE 2: Grading all transactions (5 workers)...")
            
            def grade_chunk_transactions(chunk_data):
                """Grade transactions for a single chunk"""
                i, chunk_record = chunk_data
                chunk_id = chunk_record["id"]
                
                try:
                    # Get all transactions for this chunk
                    tx_result = db.client.table("transactions").select("*").eq("video_id", chunk_id).execute()
                    transactions = tx_result.data
                    
                    if not transactions:
                        logger.info(f"📊 Chunk {i}: No transactions to grade")
                        return 0
                    
                    logger.info(f"🎯 Grading {len(transactions)} transactions for chunk {i}")
                    
                    # Grade the transactions
                    from worker.adapter import grade_transactions
                    from integrations.s3_client import put_jsonl
                    
                    grades = grade_transactions(transactions, db, chunk_record["location_id"])
                    
                    # Upload grades to S3
                    prefix = f'deriv/session={chunk_id}/'
                    put_jsonl(processing_service.s3, processing_service.settings.DERIV_BUCKET, prefix + "grades.jsonl", grades)
                    
                    # Get transaction IDs for upserting grades
                    tx_ids = [tx["id"] for tx in transactions]
                    
                    # Upsert grades to database
                    from worker.pipeline import upsert_grades
                    upsert_grades(db, tx_ids, grades)
                    
                    logger.info(f"✅ Chunk {i} grading completed: {len(grades)} grades")
                    return len(grades)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to grade chunk {i}: {e}")
                    import traceback
                    traceback.print_exc()
                    return 0
            
            # Get all transactions for the entire run_id and split into batches for parallel grading
            all_tx_result = db.client.table("transactions").select("*").eq("run_id", run_id).execute()
            all_transactions = all_tx_result.data
            
            if all_transactions:
                # Split transactions into batches for parallel processing
                batch_size = max(1, len(all_transactions) // 5)  # 5 batches
                transaction_batches = []
                for i in range(0, len(all_transactions), batch_size):
                    batch = all_transactions[i:i + batch_size]
                    transaction_batches.append((len(transaction_batches) + 1, batch))
                
                logger.info(f"📊 Found {len(all_transactions)} transactions for run_id {run_id}")
                logger.info(f"📊 Split into {len(transaction_batches)} batches for parallel grading")
                
                def grade_transactions_batch(batch_data):
                    """Grade a batch of transactions"""
                    batch_num, transactions = batch_data
                    
                    try:
                        if not transactions:
                            logger.info(f"📊 Batch {batch_num}: No transactions to grade")
                            return 0
                        
                        logger.info(f"🎯 Grading {len(transactions)} transactions in batch {batch_num}")
                        
                        # Grade the transactions
                        from worker.adapter import grade_transactions
                        from integrations.s3_client import put_jsonl
                        
                        grades = grade_transactions(transactions, db, location_id)
                        
                        # Upload grades to S3
                        prefix = f'deriv/session={run_id}/batch_{batch_num}/'
                        put_jsonl(processing_service.s3, processing_service.settings.DERIV_BUCKET, prefix + "grades.jsonl", grades)
                        
                        # Get transaction IDs for upserting grades
                        tx_ids = [tx["id"] for tx in transactions]
                        
                        # Upsert grades to database
                        from worker.pipeline import upsert_grades
                        upsert_grades(db, tx_ids, grades)
                        
                        logger.info(f"✅ Batch {batch_num} grading completed: {len(grades)} grades")
                        return len(grades)
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to grade batch {batch_num}: {e}")
                        import traceback
                        traceback.print_exc()
                        return 0
                
                # Grade batches in parallel with 5 workers
                total_grades = 0
                
                with ThreadPoolExecutor(max_workers=5) as executor:
                    # Submit all grading tasks
                    future_to_batch = {
                        executor.submit(grade_transactions_batch, batch_data): batch_data
                        for batch_data in transaction_batches
                    }
                    
                    # Collect results as they complete
                    for future in as_completed(future_to_batch):
                        batch_num, transactions = future_to_batch[future]
                        try:
                            batch_grade_count = future.result()
                            total_grades += batch_grade_count
                        except Exception as e:
                            logger.error(f"❌ Batch {batch_num} grading failed: {e}")
            else:
                logger.info("📊 No transactions found to grade")
                total_grades = 0
            
            logger.info(f"🎉 PHASE 2 COMPLETE: {total_grades} total grades processed")
            
            # PHASE 3: Process transaction audio clips and upload to Google Drive
            logger.info("🎵 PHASE 3: Processing transaction audio clips...")
            clips_processed = process_transaction_clips(run_id, wav_path, run_date, db)
            
            # PHASE 4: Clean up chunk files
            logger.info("🧹 PHASE 4: Cleaning up chunk files...")
            for i, chunk_record in enumerate(chunk_records, 1):
                chunk_path = chunk_record["meta"]["local_chunk_path"]
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    logger.info(f"🗑️ Cleaned up chunk file {i}: {chunk_path}")
            
            logger.info(f"🎉 All phases completed successfully!")
            logger.info(f"📊 Total results: {total_transactions} transactions, {total_grades} grades, {clips_processed} audio clips uploaded")
            
            return {
                "video_id": video_id,
                "run_id": run_id,
                "transactions": total_transactions,
                "grades": total_grades,
                "file_name": file_name,
                "chunks_processed": len(chunk_records),
                "clips_processed": clips_processed
            }
            
        else:
            # Process as single file (small enough)
            logger.info("🎵 Processing as single WAV file...")
            
            # Create run for the provided org and location
            logger.info("🔧 Creating run in database...")
            run_id = database_service.create_run_for_date(org_id, location_id, run_date)
            logger.info(f"✅ Created run with ID: {run_id}")
            
            # Create video record
            video_id = str(uuid.uuid4())
            
            # Parse date for started_at/ended_at
            try:
                run_datetime = datetime.strptime(run_date, "%Y-%m-%d")
                run_datetime = run_datetime.replace(tzinfo=timezone.utc)
                started_at = run_datetime
                ended_at = run_datetime + timedelta(hours=1)  # Assume 1 hour duration
            except ValueError:
                logger.warning(f"Could not parse date {run_date}, using current time")
                started_at = datetime.now(timezone.utc)
                ended_at = started_at + timedelta(hours=1)
            
            # Create video record
            video_data = {
                "id": video_id,
                "run_id": run_id,
                "location_id": location_id,
                "camera_id": f"local-wav-{file_name[:8]}",
                "s3_key": f"local/wav_processing/{video_id}/{file_name}",  # Use video_id UUID for uniqueness
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "status": "uploaded",
                "meta": {
                    "source": "local_wav_file",
                    "local_file_path": wav_path,
                    "file_name": file_name,
                    "file_size": file_size,
                    "processing_type": "local_wav_processing",
                    "organization_id": org_id  # Store org_id in meta instead
                }
            }
            
            # Insert video record
            db.client.table("videos").upsert(video_data, on_conflict="id").execute()
            logger.info(f"✅ Created video record with ID: {video_id}")
            
            # Process the WAV file
            logger.info("🚀 Starting WAV processing pipeline...")
            processing_service.process_wav_from_local_file(video_data, wav_path)
            
            # Get results
            tx_result = db.client.table("transactions").select("id", count="exact").eq("video_id", video_id).execute()
            grade_result = db.client.table("grades").select("*", count="exact").eq("video_id", video_id).execute()
            
            total_transactions = tx_result.count
            total_grades = grade_result.count
            
            logger.info(f"✅ Processing completed: {total_transactions} transactions, {total_grades} grades")
            
            # Process transaction audio clips
            logger.info("🎵 Processing transaction audio clips...")
            clips_processed = process_transaction_clips(run_id, wav_path, run_date, db)
            
            return {
                "video_id": video_id,
                "run_id": run_id,
                "transactions": total_transactions,
                "grades": total_grades,
                "file_name": file_name,
                "chunks_processed": 1,
                "clips_processed": clips_processed
            }
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    if len(sys.argv) < 5:
        print("Usage: python process_local_wav.py <filename> <org_id> <location_id> <date> [downloads_path]")
        print("Example: python process_local_wav.py \"DQ Cary_20251002-20251002_1000.wav\" org123 loc456 2025-01-02")
        print("")
        print("Arguments:")
        print("  filename      - Name of the WAV file (with or without .wav extension)")
        print("  org_id        - Organization ID")
        print("  location_id   - Location ID")
        print("  date          - Date in YYYY-MM-DD format")
        print("  downloads_path - Optional: specific path to look for the file")
        print("")
        print("The script will automatically:")
        print("1. Find the WAV file in your Downloads folder")
        print("2. Check if it needs to be split (large files)")
        print("3. Process it through the full pipeline")
        print("4. Cut transaction audio clips and upload to Google Drive")
        print("5. Clean up temporary files")
        sys.exit(1)
    
    filename = sys.argv[1]
    org_id = sys.argv[2]
    location_id = sys.argv[3]
    run_date = sys.argv[4]
    downloads_path = sys.argv[5] if len(sys.argv) > 5 else None
    
    print(f"🚀 Processing local WAV file")
    print(f"📄 File: {filename}")
    print(f"📅 Date: {run_date}")
    print(f"🏢 Org ID: {org_id}")
    print(f"📍 Location ID: {location_id}")
    if downloads_path:
        print(f"📁 Path: {downloads_path}")
    print("")
    
    result = process_local_wav(filename, org_id, location_id, run_date, downloads_path)
    
    if result:
        print(f"🎉 Processing completed successfully!")
        print(f"📊 Results:")
        print(f"   - Video ID: {result['video_id']}")
        print(f"   - Run ID: {result['run_id']}")
        print(f"   - Transactions: {result['transactions']}")
        print(f"   - Grades: {result.get('grades', 0)}")
        print(f"   - File: {result['file_name']}")
        print(f"   - Chunks processed: {result['chunks_processed']}")
        print(f"   - Audio clips uploaded: {result['clips_processed']}")
    else:
        print("❌ Processing failed.")

if __name__ == "__main__":
    main()
