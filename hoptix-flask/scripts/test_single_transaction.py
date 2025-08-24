#!/usr/bin/env python3
"""
Test script to process a single video and verify transaction timing and CSV backup.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from integrations.db_supabase import Supa
from integrations.s3_client import get_s3
from worker.pipeline import process_one_video

load_dotenv()

def test_single_transaction():
    """Test processing of a single video transaction"""
    
    print("🧪 Testing Single Transaction Processing")
    print("=" * 50)
    
    # Initialize connections
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_service_key = os.environ["SUPABASE_SERVICE_KEY"]
    aws_region = os.environ["AWS_REGION"]
    
    db = Supa(supabase_url, supabase_service_key)
    s3 = get_s3(aws_region)
    
    # Get one uploaded video
    print("📹 Fetching one uploaded video...")
    videos = db.client.table("videos").select("*").eq("status", "uploaded").limit(1).execute()
    
    if not videos.data:
        print("❌ No uploaded videos found. Please upload a video first.")
        return
    
    video = videos.data[0]
    print(f"✅ Found video: {video['s3_key']}")
    print(f"   Video ID: {video['id']}")
    print(f"   Database started_at: {video.get('started_at', 'N/A')}")
    
    # Parse video filename timestamp if it's a DT_File
    from worker.adapter import _parse_dt_file_timestamp
    if 'DT_File' in video['s3_key']:
        parsed_time = _parse_dt_file_timestamp(video['s3_key'])
        print(f"   Parsed from filename: {parsed_time}")
    else:
        print("   Not a DT_File format - will use database timestamp")
    
    print("\n🔄 Processing video...")
    
    # Check if exports directory exists (will be created during processing)
    exports_before = []
    if os.path.exists("exports"):
        exports_before = os.listdir("exports")
    
    try:
        # Process the video
        process_one_video(db, s3, video)
        
        print("\n✅ Video processing completed!")
        
        # Check what CSV files were created
        print("\n📄 CSV Backup Files Created:")
        if os.path.exists("exports"):
            exports_after = os.listdir("exports")
            new_files = [f for f in exports_after if f not in exports_before]
            for file in sorted(new_files):
                file_path = os.path.join("exports", file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    print(f"   ✅ {file} ({size} bytes)")
                    
                    # Show first few lines of CSV for verification
                    if file.endswith('.csv'):
                        print(f"      Preview of {file}:")
                        try:
                            with open(file_path, 'r') as f:
                                lines = f.readlines()[:3]  # First 3 lines
                                for line in lines:
                                    print(f"        {line.strip()[:100]}...")
                        except Exception as e:
                            print(f"        Error reading file: {e}")
        else:
            print("   ❌ No exports directory found")
        
        # Check database for inserted transactions
        print("\n💾 Database Results:")
        transactions = db.client.table("transactions").select("*").eq("video_id", video["id"]).execute()
        
        if transactions.data:
            print(f"   ✅ {len(transactions.data)} transactions inserted")
            for i, tx in enumerate(transactions.data):
                print(f"   Transaction {i+1}:")
                print(f"     ID: {tx['id']}")
                print(f"     Started: {tx['started_at']}")
                print(f"     Ended: {tx['ended_at']}")
                print(f"     TX Range: {tx['tx_range']}")
                
                # Show metadata if available
                meta = tx.get('meta', {})
                if meta:
                    print(f"     Video Seconds: {meta.get('video_start_seconds', 'N/A')}-{meta.get('video_end_seconds', 'N/A')}")
                    print(f"     Complete Order: {meta.get('complete_order', 'N/A')}")
                    print(f"     Text Preview: {str(meta.get('text', ''))[:50]}...")
        else:
            print("   ❌ No transactions found in database")
        
        # Check grades
        if transactions.data:
            grades = db.client.table("grades").select("transcript, gpt_price, score, upsell_possible, items_initial").in_("transaction_id", [tx["id"] for tx in transactions.data]).execute()
            
            if grades.data:
                print(f"\n📊 Grades Results ({len(grades.data)} records):")
                for i, grade in enumerate(grades.data):
                    print(f"   Grade {i+1}:")
                    print(f"     Transcript: {str(grade.get('transcript', ''))[:50]}...")
                    print(f"     GPT Price: ${grade.get('gpt_price', 0):.6f}")
                    print(f"     Score: {grade.get('score', 'N/A')}")
                    print(f"     Upsell Possible: {grade.get('upsell_possible', 'N/A')}")
                    print(f"     Items Initial: {grade.get('items_initial', 'N/A')}")
            else:
                print("\n❌ No grades found in database")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")

if __name__ == "__main__":
    test_single_transaction()
