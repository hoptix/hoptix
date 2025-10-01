#!/usr/bin/env python3
"""
Process a specific WAV file from Google Drive through the full pipeline
Usage: python process_wav_from_gdrive.py <file_id> <org_id> <location_id> <date>
Example: python process_wav_from_gdrive.py 1ABC123def456 org123 loc456 2025-07-15
"""

import os
import sys
import uuid
import tempfile
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrations.gdrive_client import GoogleDriveClient
from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from config import Settings
from services.database_service import DatabaseService
from services.processing_service import ProcessingService
from worker.adapter import transcribe_video, split_into_transactions, grade_transactions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_wav_from_gdrive(file_id: str, org_id: str, location_id: str, run_date: str):
    """Process a WAV file from Google Drive through the full pipeline"""
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize services
        logger.info("🔧 Initializing services...")
        settings = Settings()
        db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        s3 = get_s3(settings.AWS_REGION)
        gdrive = GoogleDriveClient()
        database_service = DatabaseService(db)
        processing_service = ProcessingService(db, settings)
        
        logger.info("✅ Services initialized successfully")
        
        # Get file information from Google Drive
        logger.info(f"🔍 Getting file information for ID: {file_id}")
        file_info = gdrive.get_file_info(file_id)
        
        if not file_info:
            logger.error(f"❌ Could not get file information for ID: {file_id}")
            return
        
        file_name = file_info.get('name', 'Unknown File')
        file_size = file_info.get('size', 0)
        mime_type = file_info.get('mimeType', 'Unknown Type')
        
        logger.info(f"📄 File name: {file_name}")
        logger.info(f"📊 File size: {file_size:,} bytes")
        logger.info(f"🎵 MIME type: {mime_type}")
        
        # Verify it's an audio file
        if not mime_type.startswith('audio/'):
            logger.warning(f"⚠️ File doesn't appear to be an audio file (MIME type: {mime_type})")
            logger.info("🔄 Proceeding anyway...")
        
        # Create a temporary file to download the WAV
        logger.info("📥 Downloading WAV file from Google Drive...")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download the file
        success = gdrive.download_file(file_id, temp_path)
        if not success:
            logger.error("❌ Failed to download file from Google Drive")
            return
        
        logger.info(f"✅ Downloaded file to: {temp_path}")
        
        # Create run for the provided org and location
        logger.info("🔧 Creating run in database...")
        run_id = database_service.create_run_for_date(org_id, location_id, run_date)
        logger.info(f"✅ Created run with ID: {run_id}")
        
        # Create video record in database
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
        
        # Generate S3 key (placeholder since we're not actually storing in S3)
        s3_key = f"gdrive/wav_processing/{file_name}"
        
        # Create video record
        video_data = {
            "id": video_id,
            "run_id": run_id,
            "location_id": location_id,
            "camera_id": f"gdrive-wav-{file_id[:8]}",
            "s3_key": s3_key,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "status": "uploaded",
            "meta": {
                "source": "google_drive_wav_file",
                "gdrive_file_id": file_id,
                "gdrive_file_name": file_name,
                "file_size": file_size,
                "mime_type": mime_type,
                "processing_type": "direct_wav_processing"
            }
        }
        
        # Insert video record
        db.client.table("videos").upsert(video_data, on_conflict="id").execute()
        logger.info(f"✅ Created video record with ID: {video_id}")
        
        # Now run the full processing pipeline
        logger.info("🚀 Starting full processing pipeline...")
        
        # Step 1: Transcribe the audio file
        logger.info("🎵 [1/6] Transcribing audio file...")
        try:
            segments = transcribe_video(temp_path)
            logger.info(f"✅ Transcription completed: {len(segments)} segments")
        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            return
        
        # Step 2: Split into transactions
        logger.info("📊 [2/6] Splitting into transactions...")
        try:
            transactions = split_into_transactions(segments, started_at.isoformat(), ended_at.isoformat())
            logger.info(f"✅ Found {len(transactions)} transactions")
        except Exception as e:
            logger.error(f"❌ Transaction splitting failed: {e}")
            return
        
        if not transactions:
            logger.warning("⚠️ No transactions found in the audio file")
            return
        
        # Step 3: Insert transactions into database
        logger.info("💾 [3/6] Inserting transactions into database...")
        try:
            from worker.pipeline import insert_transactions
            tx_ids = insert_transactions(db, video_data, transactions)
            logger.info(f"✅ Inserted {len(tx_ids)} transactions")
        except Exception as e:
            logger.error(f"❌ Transaction insertion failed: {e}")
            return
        
        # Step 4: Grade transactions
        logger.info("📝 [4/6] Grading transactions...")
        try:
            grades = grade_transactions(transactions, location_id, db)
            logger.info(f"✅ Graded {len(grades)} transactions")
        except Exception as e:
            logger.error(f"❌ Grading failed: {e}")
            return
        
        # Step 5: Store grades in database
        logger.info("💾 [5/6] Storing grades in database...")
        try:
            from worker.pipeline import upsert_grades
            upsert_grades(db, tx_ids, grades)
            logger.info(f"✅ Stored {len(grades)} grades")
        except Exception as e:
            logger.error(f"❌ Grade storage failed: {e}")
            return
        
        # Step 6: Mark video as ready
        logger.info("✅ [6/6] Marking video as ready...")
        try:
            db.client.table("videos").update({"status": "ready"}).eq("id", video_id).execute()
            logger.info("✅ Video marked as ready")
        except Exception as e:
            logger.error(f"❌ Failed to mark video as ready: {e}")
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
            logger.info("🧹 Cleaned up temporary file")
        except Exception as e:
            logger.warning(f"Could not clean up temporary file: {e}")
        
        # Summary
        logger.info("🎉 Processing completed successfully!")
        logger.info(f"📊 Summary:")
        logger.info(f"   - Video ID: {video_id}")
        logger.info(f"   - Run ID: {run_id}")
        logger.info(f"   - Transactions: {len(transactions)}")
        logger.info(f"   - Grades: {len(grades)}")
        logger.info(f"   - File: {file_name}")
        logger.info(f"   - Date: {run_date}")
        
        return {
            "video_id": video_id,
            "run_id": run_id,
            "transactions": len(transactions),
            "grades": len(grades),
            "file_name": file_name
        }
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    if len(sys.argv) != 5:
        print("Usage: python process_wav_from_gdrive.py <file_id> <org_id> <location_id> <date>")
        print("Example: python process_wav_from_gdrive.py 1ABC123def456 org123 loc456 2025-07-15")
        print("")
        print("To get the file_id:")
        print("1. Open the WAV file in Google Drive")
        print("2. Copy the file ID from the URL (the long string after /d/ and before /edit)")
        print("3. Use that as the file_id parameter")
        sys.exit(1)
    
    file_id = sys.argv[1]
    org_id = sys.argv[2]
    location_id = sys.argv[3]
    run_date = sys.argv[4]
    
    print(f"🚀 Processing WAV file from Google Drive")
    print(f"📄 File ID: {file_id}")
    print(f"📅 Date: {run_date}")
    print(f"🏢 Org ID: {org_id}")
    print(f"📍 Location ID: {location_id}")
    print("")
    
    result = process_wav_from_gdrive(file_id, org_id, location_id, run_date)
    
    if result:
        print(f"🎉 Processing completed successfully!")
        print(f"📊 Results:")
        print(f"   - Video ID: {result['video_id']}")
        print(f"   - Run ID: {result['run_id']}")
        print(f"   - Transactions: {result['transactions']}")
        print(f"   - Grades: {result['grades']}")
        print(f"   - File: {result['file_name']}")
    else:
        print("❌ Processing failed.")

if __name__ == "__main__":
    main()
