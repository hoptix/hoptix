#!/usr/bin/env python3
"""
Test script to demonstrate the download progress bar functionality.
"""

import sys
import os
from services.media import get_audio_from_gdrive
from services.database import Supa
# Add the parent directory to the path so we can import from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_download_progress():
    """
    Test the download progress bar by downloading a file from Google Drive.
    """
    try:

        
        print("🧪 Testing download progress bar...")
        print("📋 This will download an audio file and show progress")
        print("")
        
        # Test with a sample location and date
        location_id = "c3607cc3-0f0c-4725-9c42-eb2fdb5e016a"  # DQ Cary
        date = "2025-10-06"
        
        print(f"📍 Location ID: {location_id}")
        print(f"📅 Date: {date}")
        print("")
        
        # This will show the progress bar during download
        audio_path, gdrive_path = get_audio_from_gdrive(location_id, date)
        
        if audio_path:
            print(f"\n🎉 Download test completed successfully!")
            print(f"📁 Local file: {audio_path}")
            print(f"🔗 Google Drive: {gdrive_path}")
            
            # Show file info
            file_size = os.path.getsize(audio_path)
            print(f"📊 File size: {file_size:,} bytes ({file_size / (1024*1024):.1f} MB)")
            
            return True
        else:
            print(f"\n❌ Download test failed - no file downloaded")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Download Progress Bar Test")
    print("=" * 50)
    
    success = test_download_progress()
    
    if success:
        print("\n✅ Download progress bar test passed!")
        sys.exit(0)
    else:
        print("\n❌ Download progress bar test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
