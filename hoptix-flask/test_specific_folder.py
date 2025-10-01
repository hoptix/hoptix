#!/usr/bin/env python3
"""
Test script to check what files are in the specific Google Drive folder
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

def test_specific_folder():
    """Test the specific folder from the Google Drive link"""
    
    # Load environment variables
    load_dotenv()
    
    # The folder ID from your Google Drive link
    folder_id = "1d997vkf7a6b7wVJxcC99wQY4ZWIQ8QOX"
    
    try:
        # Initialize Google Drive client
        logger.info("🔧 Initializing Google Drive client...")
        gdrive = GoogleDriveClient()
        logger.info("✅ Google Drive client initialized successfully")
        
        # Try different approaches to get folder information
        logger.info(f"🔍 Getting folder information for ID: {folder_id}")
        folder_info = None
        
        # Try with different corpora settings
        try:
            folder_info = gdrive.get_file_info(folder_id)
        except Exception as e:
            logger.warning(f"Failed with default method: {e}")
        
        if not folder_info:
            # Try with allDrives corpora
            try:
                logger.info("🔄 Trying with allDrives corpora...")
                results = gdrive.service.files().get(
                    fileId=folder_id,
                    fields='id,name,size,mimeType,createdTime,modifiedTime,parents',
                    supportsAllDrives=True
                ).execute()
                folder_info = results
                logger.info("✅ Successfully accessed folder with allDrives")
            except Exception as e:
                logger.warning(f"Failed with allDrives: {e}")
        
        if not folder_info:
            logger.error(f"❌ Could not get folder information for ID: {folder_id}")
            logger.info("💡 This might be because:")
            logger.info("   - The folder is not shared with your Google account")
            logger.info("   - The folder is in a different Google Drive")
            logger.info("   - The folder requires different permissions")
            return
        
        folder_name = folder_info.get('name', 'Unknown Folder')
        logger.info(f"📁 Folder name: {folder_name}")
        
        # List all video files in the specific folder
        logger.info(f"📁 Listing all video files in folder '{folder_name}'...")
        video_files = []
        
        # Try different methods to list files
        try:
            video_files = gdrive.list_video_files_shared_with_me(folder_id)
        except Exception as e:
            logger.warning(f"Failed with shared_with_me method: {e}")
        
        if not video_files:
            # Try with allDrives method
            try:
                logger.info("🔄 Trying with allDrives method...")
                video_mimes = [
                    'video/mp4', 'video/avi', 'video/mov', 'video/quicktime',
                    'video/x-msvideo', 'video/webm', 'video/mkv', 'video/x-matroska'
                ]
                
                mime_query = ' or '.join([f"mimeType='{mime}'" for mime in video_mimes])
                query = f"('{folder_id}' in parents) and ({mime_query}) and trashed=false"
                
                results = gdrive.service.files().list(
                    q=query,
                    fields='files(id,name,size,mimeType,createdTime,modifiedTime)',
                    pageSize=1000,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    corpora='allDrives'
                ).execute()
                
                video_files = results.get('files', [])
                logger.info("✅ Successfully listed files with allDrives method")
            except Exception as e:
                logger.warning(f"Failed with allDrives method: {e}")
        
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
    test_specific_folder()
