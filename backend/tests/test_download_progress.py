import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.media import get_audio_from_location_and_date
from services.clipper import clip_transactions

if __name__ == "__main__":

    RUN_ID = "99816083-f6bd-48cf-9b4b-2a8df27c8ec4"

    audio_path, gdrive_path = get_audio_from_location_and_date(RUN_ID)

    print(f"Audio path: {audio_path}")
    print(f"Gdrive path: {gdrive_path}")

    date = "2025-10-06"

    clip_transactions(RUN_ID, audio_path, date, time_of_day_started_at="07:00:00Z")