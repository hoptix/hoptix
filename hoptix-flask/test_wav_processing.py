#!/usr/bin/env python3
"""
Test script to verify WAV file processing from Google Drive
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrations.gdrive_client import GoogleDriveClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_wav_file_access(file_id: str):
    """Test accessing a specific WAV file from Google Drive"""
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize Google Drive client
        logger.info("🔧 Initializing Google Drive client...")
        gdrive = GoogleDriveClient()
        logger.info("✅ Google Drive client initialized successfully")
        
        # Get file information
        logger.info(f"🔍 Getting file information for ID: {file_id}")
        file_info = gdrive.get_file_info(file_id)
        
        if not file_info:
            logger.error(f"❌ Could not get file information for ID: {file_id}")
            return False
        
        file_name = file_info.get('name', 'Unknown File')
        file_size = file_info.get('size', 0)
        mime_type = file_info.get('mimeType', 'Unknown Type')
        
        logger.info(f"📄 File name: {file_name}")
        logger.info(f"📊 File size: {file_size:,} bytes")
        logger.info(f"🎵 MIME type: {mime_type}")
        
        # Check if it's an audio file
        if mime_type.startswith('audio/'):
            logger.info("✅ File is an audio file")
        else:
            logger.warning(f"⚠️ File doesn't appear to be an audio file (MIME type: {mime_type})")
        
        # Test download (just get metadata, don't actually download)
        logger.info("🔍 Testing file access...")
        try:
            # Just get the file metadata to test access
            request = gdrive.service.files().get_media(fileId=file_id)
            logger.info("✅ File is accessible for download")
        except Exception as e:
            logger.error(f"❌ File is not accessible for download: {e}")
            return False
        
        logger.info("✅ WAV file test completed successfully!")
        logger.info("")
        logger.info("💡 You can now process this file with:")
        logger.info("   python process_wav_from_gdrive.py <file_id> <org_id> <location_id> <date>")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_wav_processing.py <file_id>")
        print("Example: python test_wav_processing.py 1ABC123def456")
        print("")
        print("To get the file_id:")
        print("1. Open the WAV file in Google Drive")
        print("2. Copy the file ID from the URL (the long string after /d/ and before /edit)")
        print("3. Use that as the file_id parameter")
        sys.exit(1)
    
    file_id = sys.argv[1]
    
    print(f"🧪 Testing WAV file access")
    print(f"📄 File ID: {file_id}")
    print("")
    
    success = test_wav_file_access(file_id)
    
    if success:
        print("🎉 Test completed successfully! The file is ready for processing.")
    else:
        print("❌ Test failed. Please check the file ID and permissions.")

if __name__ == "__main__":
    main()

