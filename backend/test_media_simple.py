#!/usr/bin/env python3
"""
Simple test script for media service functions
"""

import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.media import get_audio_from_gdrive

def test_get_audio_from_gdrive():
    """Test downloading DQ Cary audio from Google Drive"""
    print("🧪 Testing get_audio_from_gdrive function...")
    
    # Test parameters
    location_id = "c3607cc3-0f0c-4725-9c42-eb2fdb5e016a"
    date = "2025-10-03"  # This should match audio_2025-10-03_10-39-34.mp3
    
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

if __name__ == "__main__":
    test_get_audio_from_gdrive()
