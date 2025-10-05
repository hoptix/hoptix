#!/usr/bin/env python3
"""
Test script for media service functions
Tests audio retrieval from location and date, and Google Drive download functionality
"""

import sys
import os
import tempfile
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.media import get_audio_from_location_and_date, get_audio_from_gdrive
from services.database import Supa

def test_get_audio_from_gdrive():
    """Test downloading DQ Cary audio from Google Drive"""
    print("🧪 Testing get_audio_from_gdrive function...")
    
    # Test parameters
    location_id = "c3607cc3-0f0c-4725-9c42-eb2fdb5e016a"
    date = "2025-10-03"
    
    print(f"📍 Location ID: {location_id}")
    print(f"📅 Date: {date}")
    
    try:
        # Test the function
        audio_path = get_audio_from_gdrive(location_id, date)
        
        if audio_path:
            print(f"✅ Successfully downloaded audio to: {audio_path}")
            
            # Check if file exists and get size
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                print(f"📊 File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
                
                # Check file extension
                if audio_path.endswith('.mp3'):
                    print("✅ File is MP3 format as expected")
                else:
                    print(f"⚠️ File extension: {os.path.splitext(audio_path)[1]}")
                
                # Clean up test file
                os.remove(audio_path)
                print("🧹 Cleaned up test file")
            else:
                print("❌ Downloaded file does not exist")
        else:
            print("❌ No audio file found or download failed")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def test_get_audio_from_location_and_date():
    """Test the full audio retrieval workflow"""
    print("\n🧪 Testing get_audio_from_location_and_date function...")
    
    # Test parameters
    location_id = "c3607cc3-0f0c-4725-9c42-eb2fdb5e016a"
    date = "2025-10-03"
    
    print(f"📍 Location ID: {location_id}")
    print(f"📅 Date: {date}")
    
    try:
        # Test the function
        result = get_audio_from_location_and_date(location_id, date)
        
        if result:
            print(f"✅ Successfully retrieved audio: {result}")
            
            # If it's a file path, check if it exists
            if isinstance(result, str) and os.path.exists(result):
                file_size = os.path.getsize(result)
                print(f"📊 File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
                
                # Clean up test file
                os.remove(result)
                print("🧹 Cleaned up test file")
        else:
            print("ℹ️ No audio found or already processed")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def test_database_connection():
    """Test database connection and location lookup"""
    print("\n🧪 Testing database connection...")
    
    try:
        db = Supa()
        location_id = "c3607cc3-0f0c-4725-9c42-eb2fdb5e016a"
        
        # Test getting location name
        location_name = db.get_location_name(location_id)
        print(f"📍 Location name: {location_name}")
        
        # Test getting audio from location and date
        audio, status = db.get_audio_from_location_and_date(location_id, "2025-10-03")
        print(f"🎵 Audio in DB: {audio}")
        print(f"📊 Status: {status}")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests"""
    print("🚀 Starting Media Service Tests")
    print("=" * 50)
    
    # Test database connection first
    test_database_connection()
    
    # Test Google Drive download
    test_get_audio_from_gdrive()
    
    # Test full workflow
    test_get_audio_from_location_and_date()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
