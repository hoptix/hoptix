#!/usr/bin/env python3
"""
Google Drive Client for Voice Diarization
Clean implementation without Pydantic dependencies
"""

import os
import logging
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import io

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """
    Google Drive client for accessing voice samples and clips.
    """

    def __init__(self):
        """Initialize Google Drive API client."""
        try:
            # Get credentials from environment or file
            creds = self._get_credentials()

            # Build the service
            self.service = build('drive', 'v3', credentials=creds)

            logger.info("✅ Google Drive client initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Google Drive client: {e}")
            raise

    def _get_credentials(self):
        """Get Google Drive API credentials."""
        # Try environment variable first
        creds_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS')

        if creds_json:
            # Parse credentials from JSON string
            import json
            creds_data = json.loads(creds_json)
            return service_account.Credentials.from_service_account_info(
                creds_data,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )

        # Try file path
        creds_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH', 'credentials.json')
        if os.path.exists(creds_path):
            return service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )

        raise ValueError("Google Drive credentials not found. Set GOOGLE_DRIVE_CREDENTIALS or GOOGLE_DRIVE_CREDENTIALS_PATH")

    def list_files_in_folder(self, folder_name: str, mime_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        List files in a specific folder.

        Args:
            folder_name: Name of the folder
            mime_types: Optional list of MIME types to filter

        Returns:
            List of file metadata dictionaries
        """
        try:
            # First, find the folder
            folder_query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

            folder_results = self.service.files().list(
                q=folder_query,
                fields="files(id, name)",
                pageSize=10
            ).execute()

            folders = folder_results.get('files', [])

            if not folders:
                logger.warning(f"Folder '{folder_name}' not found")
                return []

            folder_id = folders[0]['id']
            logger.info(f"Found folder '{folder_name}' with ID: {folder_id}")

            # List files in the folder
            files_query = f"'{folder_id}' in parents and trashed=false"

            # Add MIME type filter if specified
            if mime_types:
                mime_filter = " or ".join([f"mimeType='{mt}'" for mt in mime_types])
                files_query += f" and ({mime_filter})"

            files = []
            page_token = None

            while True:
                results = self.service.files().list(
                    q=files_query,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                    pageSize=100,
                    pageToken=page_token
                ).execute()

                files.extend(results.get('files', []))
                page_token = results.get('nextPageToken')

                if not page_token:
                    break

            logger.info(f"Found {len(files)} files in '{folder_name}'")
            return files

        except Exception as e:
            logger.error(f"Error listing files in folder '{folder_name}': {e}")
            return []

    def download_file(self, file_id: str, output_path: str) -> bool:
        """
        Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID
            output_path: Local path to save the file

        Returns:
            Success boolean
        """
        try:
            request = self.service.files().get_media(fileId=file_id)

            with io.FileIO(output_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False

                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        if progress % 20 == 0:  # Log every 20%
                            logger.debug(f"Download progress: {progress}%")

            logger.info(f"Downloaded file to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return False

    def find_audio_files(self, parent_folder: str, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find audio files, optionally filtered by date.

        Args:
            parent_folder: Parent folder name
            date_str: Optional date string to filter (e.g., "2025-10-06")

        Returns:
            List of audio file metadata
        """
        audio_mime_types = [
            'audio/wav',
            'audio/x-wav',
            'audio/mpeg',
            'audio/mp3',
            'audio/mp4',
            'audio/x-m4a',
            'audio/flac',
            'audio/ogg',
            'audio/webm'
        ]

        files = self.list_files_in_folder(parent_folder, audio_mime_types)

        # Filter by date if specified
        if date_str:
            filtered = []
            for file in files:
                if date_str in file.get('name', ''):
                    filtered.append(file)
            return filtered

        return files

    def search_files(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for files using a custom query.

        Args:
            query: Google Drive API query string
            limit: Maximum number of results

        Returns:
            List of file metadata
        """
        try:
            files = []
            page_token = None

            while len(files) < limit:
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                    pageSize=min(100, limit - len(files)),
                    pageToken=page_token
                ).execute()

                files.extend(results.get('files', []))
                page_token = results.get('nextPageToken')

                if not page_token:
                    break

            return files[:limit]

        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific file.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dictionary or None
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, parents"
            ).execute()

            return file

        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return None

    def list_transaction_clips(
        self,
        folder_name: str,
        date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List transaction clips with tx_{UUID}.wav/mp3 naming pattern.

        Args:
            folder_name: Folder containing clips (e.g., "Clips_2025-10-04_0700")
            date_str: Optional date filter in folder name

        Returns:
            List of clip file metadata
        """
        import re

        # If date provided, try to find folder with date in name
        if date_str and date_str not in folder_name:
            # Search for folders with date pattern
            folder_query = (
                f"name contains '{date_str}' and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"trashed=false"
            )
            folder_results = self.service.files().list(
                q=folder_query,
                fields="files(id, name)",
                pageSize=10
            ).execute()

            folders = folder_results.get('files', [])
            if folders:
                # Use first matching folder
                folder_name = folders[0]['name']
                logger.info(f"Found clips folder: {folder_name}")

        # Get all audio files in folder
        audio_files = self.find_audio_files(folder_name)

        # Filter for transaction pattern: tx_{UUID}.ext
        tx_pattern = re.compile(r'^tx_[0-9a-fA-F-]{36}\.(wav|mp3|m4a)$', re.IGNORECASE)
        clips = []

        for file in audio_files:
            if tx_pattern.match(file.get('name', '')):
                clips.append(file)

        logger.info(f"Found {len(clips)} transaction clips in {folder_name}")
        return sorted(clips, key=lambda x: x.get('name', ''))

    def find_voice_samples_folder(
        self,
        location_name: str
    ) -> Optional[str]:
        """
        Find the voice samples folder for a location.

        Args:
            location_name: Location name (e.g., "Cary")

        Returns:
            Folder ID if found, None otherwise
        """
        # Try different naming patterns
        possible_names = [
            f"{location_name} Voice Samples",
            f"{location_name}_Voice_Samples",
            f"{location_name} Voices",
            f"Voice Samples {location_name}",
            f"Voice_Samples_{location_name}"
        ]

        for folder_name in possible_names:
            folder_query = (
                f"name='{folder_name}' and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"trashed=false"
            )

            try:
                results = self.service.files().list(
                    q=folder_query,
                    fields="files(id, name)",
                    pageSize=1
                ).execute()

                folders = results.get('files', [])
                if folders:
                    logger.info(f"Found voice samples folder: {folder_name}")
                    return folders[0]['id']

            except Exception as e:
                logger.debug(f"Error searching for {folder_name}: {e}")

        # Try partial match
        partial_query = (
            f"name contains '{location_name}' and "
            f"name contains 'Voice' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        )

        try:
            results = self.service.files().list(
                q=partial_query,
                fields="files(id, name)",
                pageSize=5
            ).execute()

            folders = results.get('files', [])
            for folder in folders:
                if 'sample' in folder['name'].lower():
                    logger.info(f"Found voice samples folder: {folder['name']}")
                    return folder['id']

        except Exception as e:
            logger.error(f"Error searching for voice samples: {e}")

        logger.warning(f"No voice samples folder found for location: {location_name}")
        return None

    def download_voice_samples(
        self,
        location_name: str,
        output_dir: str
    ) -> List[str]:
        """
        Download all voice samples for a location.

        Args:
            location_name: Location name
            output_dir: Local directory to save samples

        Returns:
            List of downloaded file paths
        """
        import os

        # Find samples folder
        folder_id = self.find_voice_samples_folder(location_name)
        if not folder_id:
            logger.error(f"Cannot find voice samples for {location_name}")
            return []

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # List audio files in folder
        files_query = (
            f"'{folder_id}' in parents and "
            f"(mimeType contains 'audio' or "
            f"name contains '.wav' or "
            f"name contains '.mp3' or "
            f"name contains '.m4a') and "
            f"trashed=false"
        )

        try:
            results = self.service.files().list(
                q=files_query,
                fields="files(id, name, mimeType)",
                pageSize=100
            ).execute()

            files = results.get('files', [])
            downloaded = []

            for file in files:
                output_path = os.path.join(output_dir, file['name'])
                if self.download_file(file['id'], output_path):
                    downloaded.append(output_path)
                    logger.info(f"Downloaded sample: {file['name']}")

            return downloaded

        except Exception as e:
            logger.error(f"Error downloading voice samples: {e}")
            return []

    def get_clips_folder_for_date(
        self,
        location_name: str,
        date_str: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find the clips folder for a specific location and date.

        Args:
            location_name: Location name (e.g., "Cary")
            date_str: Date string (e.g., "2025-10-04")

        Returns:
            Folder metadata if found
        """
        # Search for folder with location and date
        query = (
            f"name contains '{date_str}' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        )

        # Add location filter if provided
        if location_name:
            query = (
                f"(name contains '{location_name}' or "
                f"name contains 'Clips') and "
                f"{query}"
            )

        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=10
            ).execute()

            folders = results.get('files', [])

            # Prefer folders with "Clips" in name
            for folder in folders:
                if 'clips' in folder['name'].lower():
                    logger.info(f"Found clips folder: {folder['name']}")
                    return folder

            # Return first match if no "Clips" folder
            if folders:
                logger.info(f"Found folder: {folders[0]['name']}")
                return folders[0]

        except Exception as e:
            logger.error(f"Error finding clips folder: {e}")

        return None