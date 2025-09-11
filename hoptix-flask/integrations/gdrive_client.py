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

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GoogleDriveClient:
    """Client for accessing Google Drive shared drives"""
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Google Drive credentials file not found at {self.credentials_path}. "
                        "Please download it from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                logger.info("Starting OAuth flow via local server")
                logger.info("A browser window will open for authentication...")
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
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
                'video/mkv'
            ]
            
            mime_query = ' or '.join([f"mimeType='{mime}'" for mime in video_mimes])
            query = f"('{folder_id}' in parents) and ({mime_query}) and trashed=false"
            
            results = self.service.files().list(
                q=query,
                driveId=drive_id,
                corpora='drive',
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields='files(id,name,size,mimeType,createdTime,modifiedTime)'
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} video files in folder")
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing video files: {e}")
            return []
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """Download a file from Google Drive to local path"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with io.FileIO(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"Download progress: {int(status.progress() * 100)}%")
            
            logger.info(f"Successfully downloaded file to: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
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

def parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """
    Parse timestamp from DQ video filename format: DT_File20250817120001000.avi
    Format: DT_FileYYYYMMDDHHMMSSsss where sss is milliseconds
    """
    try:
        if not filename.startswith('DT_File'):
            return None
            
        # Extract timestamp part: 20250817120001000
        timestamp_part = filename[7:24]  # Skip 'DT_File' prefix
        
        if len(timestamp_part) != 17:
            return None
        
        # Parse: YYYYMMDDHHMMSS + milliseconds
        year = int(timestamp_part[:4])
        month = int(timestamp_part[4:6])
        day = int(timestamp_part[6:8])
        hour = int(timestamp_part[8:10])
        minute = int(timestamp_part[10:12])
        second = int(timestamp_part[12:14])
        millisecond = int(timestamp_part[14:17])
        
        # Create datetime with microseconds (millisecond * 1000)
        dt = datetime(year, month, day, hour, minute, second, 
                     millisecond * 1000, timezone.utc)
        
        logger.debug(f"Parsed timestamp from '{filename}': {dt.isoformat()}")
        return dt
        
    except (ValueError, IndexError) as e:
        logger.warning(f"Could not parse timestamp from filename '{filename}': {e}")
        return None
