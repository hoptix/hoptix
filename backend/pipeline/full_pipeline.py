import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import gc
from datetime import datetime

from services.database import Supa
from services.media import get_audio_from_location_and_date
from services.audio import AudioTransactionProcessor
from services.transcribe import transcribe_segments
from services.grader import grade_transactions
from services.analytics import Analytics
from services.clipper import clip_transactions
from services.transactions import format_transactions
from utils.helpers import get_memory_usage, log_memory_usage

db = Supa() 

def full_pipeline(location_id: str, date: str):
    TOTAL_STEPS = 9
    
    location_name = db.get_location_name(location_id)
    initial_memory = get_memory_usage()
    
    print(f"🚀 Starting full pipeline for {location_name} on {date}")
    print(f"📊 Initial memory usage: {initial_memory:.1f} MB")

    # 1) Check and pull audio from location and date, audio path is a temp file in your local storage
    log_memory_usage("Checking and pulling audio", 1, TOTAL_STEPS)
    try: 
        audio_path, gdrive_path = get_audio_from_location_and_date(location_id, date)
    except Exception as e: 
        print(f"❌ Error checking and pulling audio from {location_name} on {date}: {e}")
        return 

    # if we have an audio, begin the pipeline 
    if audio_path: 
        print(f"✅ Audio found: {audio_path}")
        run_id, audio_id = initialize_pipeline(location_id, date, gdrive_path)
    else: 
        return f"No audio found for {location_name} on {date}"
        
    # 2) Create audio clips and transcribe
    log_memory_usage("Creating audio clips and transcribing", 2, TOTAL_STEPS)
    
    # Create audio clips using silence detection
    audio_processor = AudioTransactionProcessor()


    # Extract original filename from gdrive_path for timestamp conversion
    # gdrive_path is a URL, so we need to construct the filename from location_id and date
    original_filename = f"audio_{date}_10-00-02.mp3" if gdrive_path else None
    print(f'🔍 DEBUG: gdrive_path: {gdrive_path}')
    print(f'🔍 DEBUG: original_filename: {original_filename}')
    
    clip_paths, begin_times, end_times, reg_begin_times, reg_end_times = audio_processor.create_audio_subclips(
        audio_path, location_id, "extracted_audio", original_filename
    )
    
    print(f"✅ Created {len([p for p in clip_paths if p])} audio clips")
    
    transcript_segments = transcribe_segments(clip_paths, begin_times, end_times)


    print(f"✅ Transcribed {len(transcript_segments)} audio clips")
    
    # Force garbage collection after transcription
    gc.collect()
    log_memory_usage("Transcription completed, memory cleaned", 2, TOTAL_STEPS)

    #3) Create transactions from transcript segments
    log_memory_usage("Creating transactions from transcript segments", 3, TOTAL_STEPS)
    transactions = format_transactions(transcript_segments, run_id, audio_id)
    print(f"📝 Created {len(transactions)} transactions")

    #4) Insert transactions into database 
    log_memory_usage(f"Inserting {len(transactions)} transactions into database", 4, TOTAL_STEPS)
    inserted_transactions = db.upsert_transactions(transactions)

    #5) Grade transactions 
    log_memory_usage("Grading transactions", 5, TOTAL_STEPS)
    grades = grade_transactions(inserted_transactions, location_id)

    #6) Upsert grades into database 
    log_memory_usage("Upserting grades into database", 6, TOTAL_STEPS)
    db.upsert_grades(grades)

    # Generate the report 
    log_memory_usage("Generating analytics report", 7, TOTAL_STEPS)
    analytics = Analytics(run_id)
    analytics.upload_to_db()

    #7) Write clips to google drive 
    log_memory_usage("Writing clips to google drive", 8, TOTAL_STEPS)
    clip_transactions(run_id, audio_path, date)

    #8) Set pipeline to complete 
    log_memory_usage("Completing pipeline", 9, TOTAL_STEPS)
    complete_pipeline(run_id, audio_id)

    final_memory = get_memory_usage()
    print(f"\n🎉 Successfully completed full pipeline!")
    print(f"📊 Memory usage: {initial_memory:.1f} MB → {final_memory:.1f} MB")
    print(f"📈 Memory efficiency: {((final_memory - initial_memory) / initial_memory * 100):+.1f}%")

    return "Successfully completed full pipeline"


def initialize_pipeline(location_id: str, date: str, gdrive_path: str):
    #insert run id 
    run_id = db.insert_run(location_id, date)

    #et the audio to processing 
    audio_exists = db.audio_exists(location_id, date)

    if not audio_exists:
        audio_id = db.create_audio(location_id, run_id, date, gdrive_path)
    else:
        audio_id = db.get_audio_id(location_id, date)

    db.set_audio_to_processing(audio_id)
    db.set_audio_link(audio_id, gdrive_path)

    return run_id, audio_id

def complete_pipeline(run_id: str, audio_id: str):
    print(f"[10/10] Completing pipeline")
    db.set_pipeline_to_complete(run_id, audio_id)
    print(f"[10/10] Pipeline completed")