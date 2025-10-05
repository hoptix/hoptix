from services.database import Supa
from services.gdrive import GoogleDriveClient
from config import Settings
from supabase import create_client, Client
from datetime import datetime
import os
import tempfile

db = Supa()
gdrive = GoogleDriveClient()

def get_audio_from_location_and_date(location_id: str, date: str):
    
    #Check if the audio is in the db with the date and location_id and return audio and status 
    audio, status = db.get_audio_from_location_and_date(location_id, date)

    #if the audio is there and status != "uploaded", say audio is already processed 
    if audio and status != "uploaded":
        return

    else: 
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
        
        # Get folder ID from location name
        folder_id = gdrive.get_folder_id_from_name(location_name)
        if not folder_id:
            print(f"❌ Folder '{location_name}' not found in 'Shared with Me'")
            return None

        else: 
            print(f"📂 Folder ID: {folder_id}")

        # Get all media files in the folder
        files = gdrive.list_media_files_shared_with_me(folder_id)
        if not files:
            print(f"❌ No media files found in folder '{location_name}'")
            # Let's also try to list ALL files to debug
            print("🔍 Debugging: Let's check what files are actually in the folder...")
            try:
                # Try to list all files without MIME type filtering
                query = f"('{folder_id}' in parents) and trashed=false"
                all_files = gdrive.service.files().list(
                    q=query,
                    fields='files(id,name,size,mimeType)',
                    corpora='user'
                ).execute()
                all_files_list = all_files.get('files', [])
                print(f"📋 Found {len(all_files_list)} total files in folder:")
                for file in all_files_list:
                    print(f"   - {file.get('name')} ({file.get('mimeType')})")
            except Exception as debug_error:
                print(f"❌ Debug query failed: {debug_error}")
            return None
        
        print(f"📋 Found {len(files)} media files in folder. Listing all files:")
        for file in files:
            file_name = file.get('name', '')
            file_size = file.get('size', 'Unknown')
            print(f"   - {file_name} ({file_size} bytes)")
        
        # Look for MP3 files matching the audio_date pattern
        # Pattern: audio_YYYY-MM-DD_HH-MM-SS.mp3
        search_pattern = f"audio_{date}_"
        print(f"🔍 Looking for files starting with: '{search_pattern}'")
        
        mp3_file = None
        matching_files = []
        
        for file in files:
            file_name = file.get('name', '')
            if file_name.startswith(search_pattern) and file_name.endswith('.mp3'):
                matching_files.append(file)
                print(f"✅ Found matching file: {file_name}")
        
        if matching_files:
            mp3_file = matching_files[0]  # Take the first match
            print(f"📥 Selected file: {mp3_file.get('name')}")
        else:
            print(f"❌ No MP3 files found matching pattern '{search_pattern}'")
            print("💡 Available audio file patterns in folder:")
            for file in files:
                file_name = file.get('name', '')
                if file_name.startswith("audio_") and file_name.endswith('.mp3'):
                    # Extract the date part
                    date_part = file_name.replace("audio_", "").split('_')[0]
                    print(f"   - audio_{date_part}_*")
        
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

    



    


