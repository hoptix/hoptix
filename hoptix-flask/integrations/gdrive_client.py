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
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from dotenv import load_dotenv

load_dotenv()


logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.file']

class GoogleDriveClient:
    """Client for accessing Google Drive (both shared drives and personal drive)"""
    
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
    
    def find_shared_drive(self, drive_name: str) -> Optional[str]:
        """Find a shared drive by name and return its ID"""
        try:
            results = self.service.drives().list().execute()
            drives = results.get('drives', [])
            
            for drive in drives:
                if drive['name'] == drive_name:
                    logger.info(f"Found shared drive '{drive_name}' with ID: {drive['id']}")
                    return drive['id']
            
            logger.warning(f"Shared drive '{drive_name}' not found")
            return None
            
        except Exception as e:
            logger.error(f"Error finding shared drive '{drive_name}': {e}")
            return None
    
    def find_folder_in_drive(self, drive_id: str, folder_name: str) -> Optional[str]:
        """Find a folder by name within a shared drive"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                driveId=drive_id,
                corpora='drive',
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            
            items = results.get('files', [])
            if items:
                folder_id = items[0]['id']
                logger.info(f"Found folder '{folder_name}' with ID: {folder_id}")
                return folder_id
            else:
                logger.warning(f"Folder '{folder_name}' not found in shared drive")
                return None
                
        except Exception as e:
            logger.error(f"Error finding folder '{folder_name}': {e}")
            return None
    
    def list_video_files(self, folder_id: str, drive_id: str) -> List[Dict]:
        """List video files in a specific folder"""
        try:
            # Query for video files (common video MIME types)
            video_mimes = [
                'video/mp4',
                'video/avi', 
                'video/mov',
                'video/quicktime',
                'video/x-msvideo',
                'video/webm',
                'video/mkv',
                'video/x-matroska'
            ]
            
            mime_query = ' or '.join([f"mimeType='{mime}'" for mime in video_mimes])
            query = f"('{folder_id}' in parents) and ({mime_query}) and trashed=false"
            
            # Handle pagination to get ALL files
            files = []
            page_token = None
            
            while True:
                results = self.service.files().list(
                    q=query,
                    driveId=drive_id,
                    corpora='drive',
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    fields='nextPageToken,files(id,name,size,mimeType,createdTime,modifiedTime)',
                    pageSize=1000,  # Maximum allowed
                    pageToken=page_token
                ).execute()
                
                page_files = results.get('files', [])
                files.extend(page_files)
                logger.info(f"Retrieved {len(page_files)} files in this page (total so far: {len(files)})")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(files)} total video files in folder")
            return files
            
        except Exception as e:
            logger.error(f"Error listing video files: {e}")
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
                    if chunks_downloaded % 10 == 0:  # Log every 10MB downloaded
                        if status:
                            progress_pct = int(status.progress() * 100)
                            logger.info(f"📊 Download progress: {progress_pct}% complete...")
                        else:
                            logger.info(f"📊 Downloaded {chunks_downloaded} MB...")
                
                fh.close()
                fh = None
                
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
    
    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get detailed information about a file"""
        try:
            file_info = self.service.files().get(
                fileId=file_id,
                fields='id,name,size,mimeType,createdTime,modifiedTime,parents'
            ).execute()
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None

    def upload_file(self, local_path: str, folder_name: str, filename: str = None) -> Optional[str]:
        """
        Upload a file to Google Drive in the specified folder.
        Returns the file ID if successful, None otherwise.
        """
        try:
            if not os.path.exists(local_path):
                logger.error(f"File not found: {local_path}")
                return None
            
            # Use provided filename or extract from local path
            if not filename:
                filename = os.path.basename(local_path)
            
            # Find the folder by name, create if it doesn't exist
            folder_id = self._find_folder_by_name(folder_name)
            if not folder_id:
                logger.info(f"Folder '{folder_name}' not found, creating it...")
                folder_id = self._create_folder(folder_name)
                if not folder_id:
                    logger.error(f"Failed to create folder '{folder_name}'")
                    return None
            
            # Check if file already exists
            existing_file_id = self._find_file_in_folder(filename, folder_id)
            if existing_file_id:
                logger.info(f"File '{filename}' already exists in folder '{folder_name}', updating...")
                # Update existing file
                file_metadata = {'name': filename}
                media = MediaFileUpload(local_path, resumable=True)
                file = self.service.files().update(
                    fileId=existing_file_id,
                    body=file_metadata,
                    media_body=media
                ).execute()
                logger.info(f"✅ Updated file '{filename}' in Google Drive (ID: {file.get('id')})")
                return file.get('id')
            else:
                # Create new file
                file_metadata = {
                    'name': filename,
                    'parents': [folder_id]
                }
                media = MediaFileUpload(local_path, resumable=True)
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                logger.info(f"✅ Uploaded file '{filename}' to Google Drive (ID: {file.get('id')})")
                return file.get('id')
                
        except Exception as e:
            logger.error(f"Failed to upload file '{local_path}': {e}")
            return None

    def _find_folder_by_name(self, folder_name: str) -> Optional[str]:
        """Find a folder by name in the shared drive"""
        try:
            # Search for folders with the exact name
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            else:
                logger.warning(f"Folder '{folder_name}' not found")
                return None
                
        except Exception as e:
            logger.error(f"Error finding folder '{folder_name}': {e}")
            return None

    def _create_folder(self, folder_name: str) -> Optional[str]:
        """Create a folder in the shared drive"""
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            logger.info(f"✅ Created folder '{folder_name}' with ID: {folder.get('id')}")
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Error creating folder '{folder_name}': {e}")
            return None

    def _find_file_in_folder(self, filename: str, folder_id: str) -> Optional[str]:
        """Find a file by name in a specific folder"""
        try:
            query = f"name='{filename}' and parents in '{folder_id}' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error finding file '{filename}' in folder: {e}")
            return None

    def find_folder_in_personal_drive(self, folder_name: str) -> Optional[str]:
        """Find a folder by name in personal Google Drive (not shared drive)"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"Found folder '{folder_name}' in personal drive with ID: {folder_id}")
                return folder_id
            else:
                logger.warning(f"Folder '{folder_name}' not found in personal drive")
                return None
                
        except Exception as e:
            logger.error(f"Error finding folder '{folder_name}' in personal drive: {e}")
            return None

    def find_folder_in_shared_with_me(self, folder_name: str) -> Optional[str]:
        """Find a folder by name in 'Shared with Me' section"""
        try:
            # Search for folders with the exact name that are shared with the user
            # Use 'user' corpora to search only in items shared with the current user
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, owners, sharedWithMeTime)",
                corpora='user'  # This searches only in items shared with the current user
            ).execute()
            
            folders = results.get('files', [])
            logger.info(f"Found {len(folders)} folders with name '{folder_name}' in user's accessible files")
            
            # Filter to only include folders that are actually shared with the user
            # (not owned by the user)
            shared_folders = []
            for folder in folders:
                # Check if the folder is shared with the user (not owned by them)
                owners = folder.get('owners', [])
                shared_with_me_time = folder.get('sharedWithMeTime')
                
                logger.info(f"Checking folder {folder['id']}: owners={len(owners)}, sharedWithMeTime={shared_with_me_time}")
                
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
                        else:
                            logger.info(f"❌ Folder {folder['id']} is owned by current user, skipping")
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
                # Let's also try to list all shared folders for debugging
                self._debug_list_shared_folders()
                return None
                
        except Exception as e:
            logger.error(f"Error finding folder '{folder_name}' in 'Shared with Me': {e}")
            return None

    def _debug_list_shared_folders(self):
        """Debug method to list all shared folders for troubleshooting"""
        try:
            logger.info("🔍 Debug: Listing all shared folders...")
            query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, owners, sharedWithMeTime)",
                corpora='user',
                pageSize=20
            ).execute()
            
            folders = results.get('files', [])
            logger.info(f"Found {len(folders)} total folders accessible to user:")
            
            for folder in folders:
                owners = folder.get('owners', [])
                shared_with_me_time = folder.get('sharedWithMeTime')
                owner_emails = [owner.get('emailAddress', '') for owner in owners] if owners else []
                
                logger.info(f"  📁 {folder['name']} (ID: {folder['id']})")
                logger.info(f"     Owners: {owner_emails}")
                logger.info(f"     Shared with me: {shared_with_me_time}")
                
        except Exception as e:
            logger.error(f"Error in debug listing: {e}")

    def list_video_files_shared_with_me(self, folder_id: str) -> List[Dict]:
        """List video files in a specific folder in 'Shared with Me'"""
        try:
            # Query for video files (common video MIME types)
            video_mimes = [
                'video/mp4',
                'video/avi', 
                'video/mov',
                'video/quicktime',
                'video/x-msvideo',
                'video/webm',
                'video/mkv',
                'video/x-matroska'
            ]
            
            mime_query = ' or '.join([f"mimeType='{mime}'" for mime in video_mimes])
            query = f"('{folder_id}' in parents) and ({mime_query}) and trashed=false"
            
            # Handle pagination to get ALL files
            files = []
            page_token = None
            
            while True:
                results = self.service.files().list(
                    q=query,
                    fields='nextPageToken,files(id,name,size,mimeType,createdTime,modifiedTime)',
                    pageSize=1000,  # Maximum allowed
                    pageToken=page_token,
                    corpora='user'  # Use 'user' corpora for shared files
                ).execute()
                
                page_files = results.get('files', [])
                files.extend(page_files)
                logger.info(f"Retrieved {len(page_files)} files in this page (total so far: {len(files)})")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(files)} total video files in folder")
            return files
            
        except Exception as e:
            logger.error(f"Error listing video files in 'Shared with Me': {e}")
            return []

    def list_video_files_personal_drive(self, folder_id: str) -> List[Dict]:
        """List video files in a specific folder in personal Google Drive"""
        try:
            # Query for video files (common video MIME types)
            video_mimes = [
                'video/mp4',
                'video/avi', 
                'video/mov',
                'video/quicktime',
                'video/x-msvideo',
                'video/webm',
                'video/mkv',
                'video/x-matroska'
            ]
            
            mime_query = ' or '.join([f"mimeType='{mime}'" for mime in video_mimes])
            query = f"('{folder_id}' in parents) and ({mime_query}) and trashed=false"
            
            # Handle pagination to get ALL files
            files = []
            page_token = None
            
            while True:
                results = self.service.files().list(
                    q=query,
                    fields='nextPageToken,files(id,name,size,mimeType,createdTime,modifiedTime)',
                    pageSize=1000,  # Maximum allowed
                    pageToken=page_token
                ).execute()
                
                page_files = results.get('files', [])
                files.extend(page_files)
                logger.info(f"Retrieved {len(page_files)} files in this page (total so far: {len(files)})")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(files)} total video files in folder")
            return files
            
        except Exception as e:
            logger.error(f"Error listing video files in personal drive: {e}")
            return []


def parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """
    Parse timestamp from video filename formats:
    1. DT_File format: DT_File{YYYYMMDDHHMMSSFFF}.avi
    2. Legacy DQ Cary format: DQ Cary_YYYYMMDD-YYYYMMDD_1000.mkv
    """
    try:
        # Try DT_File format first (new format)
        if filename.startswith('DT_File'):
            import re
            # Match DT_File format: DT_File + 17 digits (YYYYMMDDHHMMSSFFF)
            match = re.match(r'DT_File(\d{17})', filename)
            if match:
                timestamp_str = match.group(1)
                
                # Parse: YYYYMMDDHHMMSSFFF
                year = int(timestamp_str[0:4])
                month = int(timestamp_str[4:6])
                day = int(timestamp_str[6:8])
                hour = int(timestamp_str[8:10])
                minute = int(timestamp_str[10:12])
                second = int(timestamp_str[12:14])
                millisecond = int(timestamp_str[14:17])
                
                # Create datetime object
                dt = datetime(year, month, day, hour, minute, second, 
                             millisecond * 1000, timezone.utc)
                return dt
        
        # Try legacy DQ Cary format
        if filename.startswith('DQ Cary_'):
            # Extract the date part: DQ Cary_20250925-20250925_1000.mkv -> 20250925-20250925
            # Remove the prefix and suffix to get the date range
            date_part = filename[8:]  # Skip 'DQ Cary_' prefix
            if not date_part.endswith('.mkv'):
                return None
                
            # Remove .mkv extension
            date_part = date_part[:-4]
            
            # Split by underscore to get date and time parts
            parts = date_part.split('_')
            if len(parts) != 2:
                return None
            
            date_range = parts[0]  # 20250925-20250925
            time_part = parts[1]   # 1000
            
            # Parse the date range (use the first date)
            if '-' not in date_range:
                return None
                
            date_str = date_range.split('-')[0]  # 20250925
            
            if len(date_str) != 8:
                return None
            
            # Parse: YYYYMMDD
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            # Parse time part (assume HHMM format, convert to HH:MM:SS)
            if len(time_part) == 4:
                hour = int(time_part[:2])
                minute = int(time_part[2:4])
                second = 0
            else:
                # Default to start of day if time format is unexpected
                hour = 0
                minute = 0
                second = 0
            
            # Create datetime
            dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
            
            logger.debug(f"Parsed timestamp from '{filename}': {dt.isoformat()}")
            return dt
        
        # If neither format matches, return None
        return None
        
    except (ValueError, IndexError) as e:
        logger.warning(f"Could not parse timestamp from filename '{filename}': {e}")
        return None
