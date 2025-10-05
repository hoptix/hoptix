#!/usr/bin/env python3
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.gdrive import GoogleDriveClient


def find_audio_mp3s_for_date(folder_name: str, date_yyyy_mm_dd: str):
    g = GoogleDriveClient()
    folder_id = g.get_folder_id_from_name(folder_name)
    if not folder_id:
        print(f"❌ Folder not found: {folder_name}")
        return []

    files = g.list_media_files_shared_with_me(folder_id)
    print(f"📋 Total files in folder: {len(files)}")
    target_prefix = f"audio_{date_yyyy_mm_dd}_"
    matches = [f for f in files if f.get('name','').startswith(target_prefix) and f.get('name','').endswith('.mp3')]

    print(f"🔎 Looking for: {target_prefix}*.mp3")
    for f in matches:
        print(f"✅ {f['name']} ({f.get('size','?')} bytes)")
    if not matches:
        # Help debug by listing available audio dates
        audio_dates = set()
        for f in files:
            name = f.get('name','')
            if name.startswith('audio_') and name.endswith('.mp3'):
                audio_dates.add(name.split('_')[1])
        if audio_dates:
            print("💡 Available audio dates:")
            for d in sorted(audio_dates):
                print(f"   - {d}")
    return matches


def main():
    folder = os.environ.get('HOPTIX_TEST_FOLDER', 'DQ Cary')
    date = os.environ.get('HOPTIX_TEST_DATE', '2025-10-03')
    find_audio_mp3s_for_date(folder, date)


if __name__ == '__main__':
    main()
