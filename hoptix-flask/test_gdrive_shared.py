#!/usr/bin/env python3
"""
Test script to verify Google Drive "Shared with Me" functionality
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

def test_shared_with_me():
    """Test finding and listing files in the DQ Cary folder from Shared with Me"""
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize Google Drive client
        logger.info("🔧 Initializing Google Drive client...")
        gdrive = GoogleDriveClient()
        logger.info("✅ Google Drive client initialized successfully")
        
        # Test finding the DQ Cary folder
        folder_name = "DQ Cary"
        logger.info(f"🔍 Searching for folder: '{folder_name}'")
        
        folder_id = gdrive.find_folder_in_shared_with_me(folder_name)
        
        if not folder_id:
            logger.error(f"❌ Folder '{folder_name}' not found in Shared with Me")
            return
        
        logger.info(f"✅ Found folder '{folder_name}' with ID: {folder_id}")
        
        # List all video files in the folder
        logger.info(f"📁 Listing all video files in folder '{folder_name}'...")
        video_files = gdrive.list_video_files_shared_with_me(folder_id)
        
        if not video_files:
            logger.warning(f"⚠️ No video files found in folder '{folder_name}'")
        else:
            logger.info(f"✅ Found {len(video_files)} video files:")
            
            for i, file_info in enumerate(video_files, 1):
                file_id = file_info.get('id', 'Unknown ID')
                file_name = file_info.get('name', 'Unknown Name')
                file_size = file_info.get('size', 0)
                mime_type = file_info.get('mimeType', 'Unknown Type')
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
                
                logger.info(f"  {i:2d}. 📄 {file_name}")
                logger.info(f"      🆔 ID: {file_id}")
                logger.info(f"      📊 Size: {size_str}")
                logger.info(f"      🎬 Type: {mime_type}")
                logger.info(f"      📅 Created: {created_time}")
                logger.info(f"      📅 Modified: {modified_time}")
                logger.info("")
        
        # Also test listing all files (not just videos) for debugging
        logger.info("🔍 Debug: Listing ALL files in the folder (not just videos)...")
        try:
            # Query for all files (not just videos)
            query = f"('{folder_id}' in parents) and trashed=false"
            results = gdrive.service.files().list(
                q=query,
                fields='files(id,name,size,mimeType,createdTime,modifiedTime)',
                pageSize=1000,
                corpora='user'
            ).execute()
            
            all_files = results.get('files', [])
            logger.info(f"📁 Found {len(all_files)} total files in folder:")
            
            for i, file_info in enumerate(all_files, 1):
                file_name = file_info.get('name', 'Unknown Name')
                mime_type = file_info.get('mimeType', 'Unknown Type')
                is_folder = mime_type == 'application/vnd.google-apps.folder'
                
                icon = "📁" if is_folder else "📄"
                logger.info(f"  {i:2d}. {icon} {file_name} ({mime_type})")
                
        except Exception as e:
            logger.error(f"Error listing all files: {e}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_shared_with_me()
