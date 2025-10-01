#!/usr/bin/env python3
"""
List WAV files in your personal Google Drive to help find file IDs
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

def list_wav_files():
    """List WAV files in personal Google Drive"""
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize Google Drive client
        logger.info("🔧 Initializing Google Drive client...")
        gdrive = GoogleDriveClient()
        logger.info("✅ Google Drive client initialized successfully")
        
        # Search for WAV files in personal drive
        logger.info("🔍 Searching for WAV files in personal Google Drive...")
        
        # Query for WAV files
        query = "mimeType='audio/wav' and trashed=false"
        results = gdrive.service.files().list(
            q=query,
            fields='files(id,name,size,mimeType,createdTime,modifiedTime)',
            pageSize=100,
            orderBy='modifiedTime desc'  # Most recent first
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            logger.info("ℹ️ No WAV files found in your personal Google Drive")
            return
        
        logger.info(f"✅ Found {len(files)} WAV files:")
        logger.info("")
        
        for i, file_info in enumerate(files, 1):
            file_id = file_info.get('id', 'Unknown ID')
            file_name = file_info.get('name', 'Unknown Name')
            file_size = file_info.get('size', 0)
            created_time = file_info.get('createdTime', 'Unknown')
            modified_time = file_info.get('modifiedTime', 'Unknown')
            
            # Convert size to human readable format
            if file_size:
                try:
                    file_size = int(file_size)
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    elif file_size < 1024 * 1024 * 1024:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"
                except (ValueError, TypeError):
                    size_str = "Unknown size"
            else:
                size_str = "Unknown size"
            
            logger.info(f"  {i:2d}. 🎵 {file_name}")
            logger.info(f"      🆔 ID: {file_id}")
            logger.info(f"      📊 Size: {size_str}")
            logger.info(f"      📅 Created: {created_time}")
            logger.info(f"      📅 Modified: {modified_time}")
            logger.info("")
        
        logger.info("💡 To process a WAV file, use:")
        logger.info("   python process_wav_from_gdrive.py <file_id> <org_id> <location_id> <date>")
        logger.info("")
        logger.info("Example:")
        if files:
            first_file_id = files[0].get('id', 'FILE_ID')
            logger.info(f"   python process_wav_from_gdrive.py {first_file_id} org123 loc456 2025-07-15")
        
    except Exception as e:
        logger.error(f"❌ Failed to list WAV files: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_wav_files()
