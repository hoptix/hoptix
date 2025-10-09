#!/usr/bin/env python3
"""
Test script to verify the new proper file chunking approach works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from services.transcribe import transcribe_audio
from services.database import Supa
from config import Settings

def test_new_chunking_approach():
    """Test the new chunking approach with a sample audio file"""
    
    # Initialize services
    settings = Settings()
    db = Supa()
    
    # Test with a sample audio file (you'll need to provide a real file path)
    audio_path = "/tmp/test_audio.mp3"  # Replace with actual file path
    
    if not os.path.exists(audio_path):
        print(f"❌ Test audio file not found: {audio_path}")
        print("Please provide a real audio file path to test")
        return False
    
    # Create a test audio record (matching audios table schema)
    audio_record = {
        "id": "test-audio-123",
        "run_id": "test-run-123", 
        "location_id": "test-location-123",
        "date": "2025-01-08",
        "started_at": "2025-01-08T10:00:00Z",
        "ended_at": "2025-01-08T18:00:00Z",
        "link": "test/audio/test.mp3",
        "status": "processing"
    }
    
    print(f"🧪 Testing new chunking approach with: {audio_path}")
    print(f"📊 File size: {os.path.getsize(audio_path) / (1024*1024):.1f} MB")
    
    try:
        # Test the new transcribe function
        segments = transcribe_audio(audio_path, db=db, audio_record=audio_record)
        
        print(f"✅ Transcription completed successfully!")
        print(f"📝 Total segments: {len(segments)}")
        
        if segments:
            print(f"📊 Sample segments:")
            for i, segment in enumerate(segments[:3]):  # Show first 3 segments
                print(f"   {i+1}. {segment['start']:.1f}s - {segment['end']:.1f}s: {segment['text'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_new_chunking_approach()
    if success:
        print("\n🎉 New chunking approach test passed!")
    else:
        print("\n❌ New chunking approach test failed!")
        sys.exit(1)
