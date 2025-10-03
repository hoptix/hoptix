


from services.database_service import DatabaseService
from services.media import get_audio_from_location_and_date
from services.transcribe import transcribe_audio
from services.transactions import split_into_transactions
from services.grader import grade_transactions
from services.database_service import insert_transactions
from services.database_service import upsert_grades
from services.report import generate_report
from services.google_drive import write_clips_to_google_drive
from services.voice_diarization import conduct_voice_diarization
from services.voice_diarization import insert_voice_diarization

db = DatabaseService()

def full_pipeline(location_id: str, date: str):

    location_name = db.get_location_name(location_id)

    print(f"Processing full pipeline for {location_name} on {date}")


    # 1) Check and pull audio from location and date
    audio_path, gdrive_path = get_audio_from_location_and_date(location_id, date)

    # if we have an audio, begin the pipeline 
    if audio_path: 
        run_id = initialize_pipeline(location_id, date, gdrive_path)

    else: 
        return "No audio found for {location_name} on {date}"
        

    # 2) Transcribe video to audio 
    transcript_segments = transcribe_audio(audio_path)

    #3) Split audio into transactions 
    transactions = split_into_transactions(transcript_segments)


    #4) Grade transactions 
    grades = grade_transactions(transactions)

    #5) Insert transactions into database 
    insert_transactions(transactions)

    #6) Upsert grades into database 
    upsert_grades(grades)

    # Generate the report 
    generate_report(run_id)


    #6) Write clips to google drive 
    write_clips_to_google_drive(run_id)

    #7) Conduct voice diarization 
    conduct_voice_diarization(run_id)

    #8) Insert voice diarization into database 
    insert_voice_diarization(run_id)

    return "Successfully completed full pipeline"


def initialize_pipeline(location_id: str, date: str, gdrive_path: str):
    
    run_id = db.insert_run(location_id, date, gdrive_path)
    return run_id