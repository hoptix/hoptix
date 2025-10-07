import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.database import Supa




from pipeline.full_pipeline import full_pipeline

if __name__ == "__main__":
    db = Supa()
    db.set_audio_status("f2a5d224-9f14-4a5e-b40b-c91ea95402bf", "uploaded")
    full_pipeline("c3607cc3-0f0c-4725-9c42-eb2fdb5e016a", "2025-10-08")







