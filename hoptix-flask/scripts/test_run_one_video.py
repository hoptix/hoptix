#!/usr/bin/env python3
"""
Test script for the /run-one-video endpoint

This script will:
1. Create test data in the database (org, location, run, video)
2. Enqueue the video to SQS 
3. Test the /run-one-video endpoint
4. Verify the results
"""

import os
import sys
import uuid
import requests
import json
import datetime as dt
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Settings
from integrations.db_supabase import Supa
from integrations.sqs_client import get_sqs_client

# Load environment
load_dotenv()

# Configuration
FLASK_BASE_URL = os.getenv("FLASK_BASE_URL", "http://localhost:8000")
TEST_S3_KEY = "test/sample_video.mp4"  # This doesn't need to exist for endpoint testing

def create_test_data():
    """Create test data in database"""
    print("🔧 Creating test data...")
    
    settings = Settings()
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    
    # Generate UUIDs
    org_id = str(uuid.uuid4())
    location_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    
    try:
        # Create org
        db.client.table("orgs").upsert({
            "id": org_id,
            "name": "Test Org"
        }, on_conflict="id").execute()
        print(f"  ✅ Created org: {org_id}")
        
        # Create location
        db.client.table("locations").upsert({
            "id": location_id,
            "org_id": org_id,
            "name": "Test Location"
        }, on_conflict="id").execute()
        print(f"  ✅ Created location: {location_id}")
        
        # Create run
        db.client.table("runs").upsert({
            "id": run_id,
            "org_id": org_id,
            "location_id": location_id,
            "run_date": dt.date.today().isoformat()
        }, on_conflict="id").execute()
        print(f"  ✅ Created run: {run_id}")
        
        # Create video
        now = dt.datetime.now(dt.timezone.utc)
        start_time = now - dt.timedelta(minutes=5)
        end_time = now
        
        video_result = db.client.table("videos").insert({
            "run_id": run_id,
            "location_id": location_id,
            "station_id": "test_camera_1",
            "s3_key": TEST_S3_KEY,
            "started_at": start_time.isoformat(),
            "ended_at": end_time.isoformat(),
            "status": "uploaded"  # Ready for processing
        }).execute()
        
        video_id = video_result.data[0]["id"]
        print(f"  ✅ Created video: {video_id}")
        
        return {
            "org_id": org_id,
            "location_id": location_id,
            "run_id": run_id,
            "video_id": video_id,
            "video_data": {
                "id": video_id,
                "s3_key": TEST_S3_KEY,
                "run_id": run_id,
                "location_id": location_id,
                "started_at": start_time.isoformat(),
                "ended_at": end_time.isoformat()
            }
        }
        
    except Exception as e:
        print(f"  ❌ Error creating test data: {e}")
        raise

def enqueue_to_sqs(video_data):
    """Enqueue video to SQS"""
    print("📤 Enqueuing video to SQS...")
    
    try:
        settings = Settings()
        sqs_client = get_sqs_client(
            settings.AWS_REGION,
            settings.SQS_QUEUE_URL,
            settings.SQS_DLQ_URL
        )
        
        message_id = sqs_client.send_video_message(video_data)
        print(f"  ✅ Enqueued video to SQS: {message_id}")
        
        # Check queue stats
        queue_stats = sqs_client.get_queue_attributes()
        print(f"  📊 Queue stats: {queue_stats}")
        
        return message_id
        
    except Exception as e:
        print(f"  ❌ Error enqueuing to SQS: {e}")
        raise

def test_run_one_video_endpoint():
    """Test the /run-one-video endpoint"""
    print("🧪 Testing /run-one-video endpoint...")
    
    try:
        # Make request to the endpoint
        response = requests.post(f"{FLASK_BASE_URL}/runs/run-one-video", timeout=30)
        
        print(f"  📡 Response Status: {response.status_code}")
        print(f"  📄 Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Success: {result.get('message', 'No message')}")
            return True
        elif response.status_code == 404:
            print("  ⚠️ No videos to process (queue might be empty)")
            return False
        else:
            print(f"  ❌ Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
        print("  💡 Make sure your Flask app is running on http://localhost:8000")
        return False

def check_video_status(video_id):
    """Check the final status of the video"""
    print("🔍 Checking video processing status...")
    
    try:
        settings = Settings()
        db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        
        result = db.client.table("videos").select("status").eq("id", video_id).execute()
        
        if result.data:
            status = result.data[0]["status"]
            print(f"  📊 Final video status: {status}")
            
            if status == "ready":
                print("  ✅ Video processed successfully!")
                return True
            elif status == "failed":
                print("  ❌ Video processing failed")
                return False
            else:
                print(f"  ⏳ Video still in status: {status}")
                return False
        else:
            print("  ❌ Video not found")
            return False
            
    except Exception as e:
        print(f"  ❌ Error checking status: {e}")
        return False

def cleanup_test_data(test_data):
    """Clean up test data"""
    print("🧹 Cleaning up test data...")
    
    try:
        settings = Settings()
        db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        
        # Delete in reverse order due to foreign keys
        db.client.table("videos").delete().eq("id", test_data["video_id"]).execute()
        db.client.table("runs").delete().eq("id", test_data["run_id"]).execute()
        db.client.table("locations").delete().eq("id", test_data["location_id"]).execute()
        db.client.table("orgs").delete().eq("id", test_data["org_id"]).execute()
        
        print("  ✅ Test data cleaned up")
        
    except Exception as e:
        print(f"  ⚠️ Error during cleanup: {e}")

def main():
    """Main test function"""
    print("🚀 Starting /run-one-video endpoint test")
    print("=" * 50)
    
    test_data = None
    
    try:
        # 1. Create test data
        test_data = create_test_data()
        
        # 2. Enqueue to SQS
        message_id = enqueue_to_sqs(test_data["video_data"])
        
        # 3. Test the endpoint
        print("\n⏳ Waiting 2 seconds for SQS message to be available...")
        import time
        time.sleep(2)
        
        success = test_run_one_video_endpoint()
        
        if success:
            # 4. Check final status
            print("\n⏳ Waiting 3 seconds for processing to complete...")
            time.sleep(3)
            check_video_status(test_data["video_id"])
        
        print("\n" + "=" * 50)
        print("🏁 Test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        
    finally:
        # Cleanup
        if test_data:
            cleanup_test_data(test_data)

def check_prerequisites():
    """Check if all prerequisites are met"""
    print("🔍 Checking prerequisites...")
    
    # Check environment variables
    required_vars = [
        "SUPABASE_URL", "SUPABASE_SERVICE_KEY", 
        "AWS_REGION", "SQS_QUEUE_URL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    # Check if Flask app is running
    try:
        response = requests.get(f"{FLASK_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Flask app is running")
        else:
            print(f"⚠️ Flask app responded with status {response.status_code}")
    except:
        print("❌ Flask app is not running or not accessible")
        print(f"   Make sure your Flask app is running on {FLASK_BASE_URL}")
        return False
    
    print("✅ Prerequisites check passed")
    return True

if __name__ == "__main__":
    if not check_prerequisites():
        print("\n💡 To fix:")
        print("   1. Make sure all environment variables are set")
        print("   2. Start your Flask app: python app.py")
        print("   3. Run this test again")
        sys.exit(1)
    
    main()
