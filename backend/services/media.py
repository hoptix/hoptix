from services.database_service import DatabaseService
from services.gdrive import GoogleDriveClient
from config import Settings
from supabase import create_client, Client
from datetime import datetime
import os
import tempfile

db = DatabaseService()
gdrive = GoogleDriveClient()

def get_audio_from_location_and_date(location_id: str, date: str):
    
    #Check if the audio is in the db with the date and location_id and return audio and status 
    audio, status = db.get_audio_from_location_and_date(location_id, date)

    #if the audio is there and status != "uploaded", say audio is already processed 
    if audio and status != "uploaded":
        return

    #if the audio is there and status = "uploaded", download the audio from gdrive
    if audio and status == "uploaded":
        audio = get_audio_from_gdrive(location_id, date)
        return audio

    #if the audio is not there, download it to google drive and upload it to the supabase 
    if not audio: 
        #get from google drive 
        audio = get_audio_from_gdrive(location_id, date)
        return audio
    

def get_audio_from_gdrive(location_id: str, date: str):
    """
    Download DQ Cary MP3 audio from Google Drive for a specific location and date.
    
    Args:
        location_id (str): The location ID to get the location name from
        date (str): Date in YYYY-MM-DD format
        
    Returns:
        str: Local path to downloaded MP3 file
    """

    try:
        # Get location name from location_id
        location_name = db.get_location_name(location_id)
        if not location_name:
            raise ValueError(f"Location {location_id} not found")
        
        print(f"📍 Location: {location_name}")
        
        # Convert date from YYYY-MM-DD to YYYYMMDD format
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%Y%m%d")
        

        search_pattern = f"{location_name}_{date_formatted}-{date_formatted}"
        
        # Search Google Drive for files matching the pattern
        files = gdrive.list_media_files_shared_with_me(search_pattern)

        if not files:
            print(f"❌ No files found for date {date}")
            return None
        
        # Look for MP3 files only
        mp3_file = None
        for file in files:
            file_name = file.get('name', '')
            if file_name.startswith(search_pattern) and file_name.endswith('.mp3'):
                mp3_file = file
                break
        
        if not mp3_file:
            print(f"❌ No MP3 files found for date {date}")
            return None
        
        file_id = mp3_file['id']
        file_name = mp3_file['name']
        print(f"📥 Found MP3 file: {file_name}")
        
        # Create temporary MP3 file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tmp_audio_path = tmp_file.name
        
        # Download the MP3 file
        print(f"⬇️ Downloading {file_name} to {tmp_audio_path}")
        if gdrive.download_file(file_id, tmp_audio_path):
            file_size = os.path.getsize(tmp_audio_path)
            print(f"✅ Downloaded {file_name} ({file_size:,} bytes)")

            return tmp_audio_path

        else:
            print(f"❌ Failed to download {file_name}")
            # Clean up failed download
            if os.path.exists(tmp_audio_path):
                os.remove(tmp_audio_path)
            return None
    
    except Exception as e:
        print(f"❌ Error downloading DQ Cary MP3: {e}")
        return None

    



    


