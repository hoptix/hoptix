# Google Drive client for media file operations

import os
import io
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.file']

class GoogleDriveClient:
    """Client for accessing Google Drive files in 'Shared with Me'"""
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        
        # Check if token file exists and warn about scope changes
        if os.path.exists(self.token_path):
            logger.warning(f"Token file {self.token_path} exists. If you're getting scope errors, delete this file to re-authenticate with new scopes.")
        
        # Try to get credentials from environment variables first (for production)
        google_creds_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS')
        if google_creds_json:
            try:
                creds_info = json.loads(google_creds_json)
                creds = Credentials.from_authorized_user_info(creds_info, SCOPES)
                logger.info("Using Google Drive credentials from environment variables")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing Google Drive credentials from environment: {e}")
                raise ValueError("Invalid Google Drive credentials in environment variable")
        
        # Fallback to file-based authentication (for development)
        elif os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
                logger.info("Using Google Drive credentials from token file")
            except Exception as e:
                logger.error(f"Error loading credentials from token file: {e}")
                logger.info("This might be due to scope changes. Please delete the token file and re-authenticate.")
                raise
        
        # Refresh credentials if needed
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Successfully refreshed Google Drive credentials")
            except Exception as e:
                logger.error(f"Error refreshing Google Drive credentials: {e}")
                raise
        
        # Interactive authentication (development only)
        elif not creds or not creds.valid:
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(
                    f"Google Drive credentials not found. Please set GOOGLE_DRIVE_CREDENTIALS "
                    f"environment variable or provide {self.credentials_path} file."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES)
            logger.info("Starting OAuth flow via local server")
            logger.info("A browser window will open for authentication...")
            creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run (development only)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        if not creds or not creds.valid:
            raise ValueError("Unable to obtain valid Google Drive credentials")
        
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully authenticated with Google Drive API")
    
    def get_folder_id_from_name(self, folder_name: str) -> Optional[str]:
        """Get folder ID from folder name in 'Shared with Me'"""
        return self.find_folder_in_shared_with_me(folder_name)
    
    def find_folder_in_shared_with_me(self, folder_name: str) -> Optional[str]:
        """Find a folder by name in 'Shared with Me' section"""
        try:
            # Search for folders with the exact name that are shared with the user
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, owners, sharedWithMeTime)",
                corpora='user'  # This searches only in items shared with the current user
            ).execute()
            
            folders = results.get('files', [])
            logger.info(f"Found {len(folders)} folders with name '{folder_name}' in user's accessible files")
            
            # Filter to only include folders that are actually shared with the user
            shared_folders = []
            for folder in folders:
                # Check if the folder is shared with the user (not owned by them)
                owners = folder.get('owners', [])
                shared_with_me_time = folder.get('sharedWithMeTime')
                
                # If it has a sharedWithMeTime, it's definitely shared with the user
                if shared_with_me_time:
                    shared_folders.append(folder)
                    logger.info(f"✅ Found shared folder '{folder_name}' with ID: {folder['id']} (shared on: {shared_with_me_time})")
                # If no sharedWithMeTime but has owners, check if user is not the owner
                elif owners:
                    # Get current user's email to compare with owners
                    try:
                        about = self.service.about().get(fields='user').execute()
                        current_user_email = about.get('user', {}).get('emailAddress', '')
                        
                        # Check if current user is not in the owners list
                        owner_emails = [owner.get('emailAddress', '') for owner in owners]
                        if current_user_email not in owner_emails:
                            shared_folders.append(folder)
                            logger.info(f"✅ Found shared folder '{folder_name}' with ID: {folder['id']} (not owned by current user: {current_user_email})")
                    except Exception as e:
                        logger.warning(f"Could not verify ownership for folder {folder['id']}: {e}")
                        # If we can't verify, include it as a potential shared folder
                        shared_folders.append(folder)
                        logger.info(f"⚠️ Including folder {folder['id']} due to ownership verification failure")
            
            if shared_folders:
                folder_id = shared_folders[0]['id']
                logger.info(f"✅ Selected folder '{folder_name}' in 'Shared with Me' with ID: {folder_id}")
                return folder_id
            else:
                logger.warning(f"❌ Folder '{folder_name}' not found in 'Shared with Me'")
                return None
                
        except Exception as e:
            logger.error(f"Error finding folder '{folder_name}' in 'Shared with Me': {e}")
            return None

    def list_media_files_shared_with_me(self, folder_id: str) -> List[Dict]:
        """List video and audio files in a specific folder in 'Shared with Me'"""
        try:
            # First, let's try to list ALL files in the folder to debug
            query = f"('{folder_id}' in parents) and trashed=false"
            files = []
            page_token = None
            while True:
                results = self.service.files().list(
                    q=query,
                    fields='nextPageToken,files(id,name,size,mimeType,createdTime,modifiedTime)',
                    pageSize=1000,
                    pageToken=page_token,
                    corpora='user'
                ).execute()
                page_files = results.get('files', [])
                files.extend(page_files)
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(files)} total files in folder (all types)")
            
            # Now filter for media files
            video_mimes = [
                'video/mp4','video/avi','video/mov','video/quicktime','video/x-msvideo','video/webm','video/mkv','video/x-matroska'
            ]
            audio_mimes = [
                'audio/wav','audio/x-wav','audio/mpeg','audio/mp3','audio/mp4','audio/aac','audio/x-m4a','audio/ogg','audio/flac'
            ]
            media_mimes = video_mimes + audio_mimes
            
            media_files = []
            for file in files:
                mime_type = file.get('mimeType', '')
                if mime_type in media_mimes:
                    media_files.append(file)
            
            logger.info(f"Found {len(media_files)} media files after filtering")
            return media_files
            
        except Exception as e:
            logger.error(f"Error listing media files in 'Shared with Me': {e}")
            return []

    def download_file(self, file_id: str, local_path: str, max_retries: int = 5) -> bool:
        """Download a file from Google Drive to local path with retry logic"""
        import time
        import ssl
        import random
        
        # Get file metadata for logging
        file_name = "Unknown"
        try:
            file_metadata = self.service.files().get(fileId=file_id, fields="name,size").execute()
            file_name = file_metadata.get('name', 'Unknown')
            file_size = int(file_metadata.get('size', 0))
            logger.info(f"📥 Starting download: {file_name} ({file_size:,} bytes)")
        except Exception as e:
            logger.info(f"📥 Starting download from Google Drive (file ID: {file_id})")
            logger.debug(f"Could not get file metadata: {e}")
        
        for attempt in range(max_retries):
            fh = None
            try:
                # Add random jitter to avoid thundering herd
                if attempt > 0:
                    jitter = random.uniform(0.5, 2.0)
                    logger.info(f"⏳ Retry attempt {attempt + 1}/{max_retries} in {jitter:.1f}s...")
                    time.sleep(jitter)
                
                logger.info(f"🔄 Downloading from Google Drive (attempt {attempt + 1}/{max_retries})...")
                request = self.service.files().get_media(fileId=file_id)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                fh = io.FileIO(local_path, 'wb')
                downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)  # 1MB chunks
                done = False
                chunks_downloaded = 0
                
                while done is False:
                    status, done = downloader.next_chunk()
                    chunks_downloaded += 1
                    
                    if status:
                        progress_pct = int(status.progress() * 100)
                        # Create a simple progress bar
                        bar_length = 30
                        filled_length = int(bar_length * status.progress())
                        bar = '█' * filled_length + '░' * (bar_length - filled_length)
                        
                        # Show progress every 5% or every 5MB
                        if progress_pct % 5 == 0 or chunks_downloaded % 5 == 0:
                            logger.info(f"📊 Download progress: [{bar}] {progress_pct}% ({chunks_downloaded}MB)")
                    else:
                        # Fallback when status is not available
                        if chunks_downloaded % 5 == 0:  # Log every 5MB
                            logger.info(f"📊 Downloaded {chunks_downloaded} MB...")
                
                fh.close()
                fh = None
                
                # Show final progress bar completion
                final_bar = '█' * 30
                logger.info(f"📊 Download complete: [{final_bar}] 100% ({chunks_downloaded}MB)")
                
                # Get actual file size for logging
                actual_size = os.path.getsize(local_path)
                logger.info(f"✅ Successfully downloaded {file_name} ({actual_size:,} bytes) to: {local_path}")
                return True
                
            except (ssl.SSLError, ConnectionError, OSError, TimeoutError) as e:
                # Clean up file handle
                if fh:
                    try:
                        fh.close()
                    except:
                        pass
                    fh = None
                
                # Clean up partial file
                try:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                        logger.debug(f"Cleaned up partial download: {local_path}")
                except:
                    pass
                
                if attempt < max_retries - 1:
                    wait_time = min((attempt + 1) * 3, 15)  # Cap at 15 seconds
                    logger.warning(f"❌ Download attempt {attempt + 1}/{max_retries} failed: {str(e)[:100]}")
                    logger.info(f"⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"💥 Download failed after {max_retries} attempts: {str(e)[:100]}")
                    return False
                    
            except Exception as e:
                # Clean up file handle
                if fh:
                    try:
                        fh.close()
                    except:
                        pass
                    fh = None
                
                # Clean up partial file
                try:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                except:
                    pass
                    
                logger.error(f"Unexpected download error: {str(e)[:50]}")
                return False
        
        return False
