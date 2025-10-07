import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from services.database import Supa

from services.media import get_audio_from_location_and_date
from services.transcribe import transcribe_audio
from services.transactions import split_into_transactions
from services.grader import grade_transactions
from services.analytics import Analytics


db = Supa() 

def full_pipeline(location_id: str, date: str):

    location_name = db.get_location_name(location_id)

    print(f"Processing full pipeline for {location_name} on {date}")

    # 1) Check and pull audio from location and date, audio path is a temp file in your local storage
    print(f"Checking and pulling audio from {location_name} on {date}")

    try: 
        audio_path, gdrive_path = get_audio_from_location_and_date(location_id, date)
    except Exception as e:
        print(f"Error checking and pulling audio from {location_name} on {date}: {e}")
        return 

    # if we have an audio, begin the pipeline 
    if audio_path: 
        run_id, audio_id = initialize_pipeline(location_id, date, gdrive_path)

    else: 
        return "No audio found for {location_name} on {date}"
        
    # 2) Transcribe audio to text 
    transcript_segments = transcribe_audio(audio_path)

    #3) Split audio into transactions 
    transactions = split_into_transactions(transcript_segments, date=date)
    print(f"Split {len(transactions)} transactions")

    #4) Insert transactions into database 
    db.upsert_transactions(transactions)

    #5) Grade transactions 
    grades = grade_transactions(transactions, location_id)



    #6) Upsert grades into database 
    db.upsert_grades(grades)

    # Generate the report 
    analytics = Analytics(run_id)
    analytics.generate_report()


    # #6) Write clips to google drive 
    # write_clips_to_google_drive(run_id)

    # #7) Conduct voice diarization 
    # conduct_voice_diarization(run_id)

    # #8) Insert voice diarization into database 
    # insert_voice_diarization(run_id)

    #9) Set pipeline to complete 
    complete_pipeline(run_id, audio_id)

    return "Successfully completed full pipeline"


def initialize_pipeline(location_id: str, date: str, gdrive_path: str):
    #insert run id 
    run_id = db.insert_run(location_id, date)

    #et the audio to processing 
    audio_exists = db.audio_exists(location_id, date)

    if not audio_exists:
        audio_id = db.create_audio(location_id, date, gdrive_path)
    else:
        audio_id = db.get_audio_id(location_id, date)

    db.set_audio_to_processing(audio_id)
    db.set_audio_link(audio_id, gdrive_path)

    return run_id, audio_id

def complete_pipeline(run_id: str, audio_id: str):
    db.set_pipeline_to_complete(run_id)