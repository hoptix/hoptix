#!/usr/bin/env python3
"""
Test script for the new audio-based chunking approach.
This script tests the complete chunking system with database integration.
"""

import sys
import os
# Add the parent directory to the path so we can import from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psutil
import time
from services.transcribe import transcribe_audio, get_memory_usage
from services.database import Supa
from config import Settings

def test_audio_chunking_with_db(audio_path: str):
    """
    Test the complete audio chunking system with database integration.
    """
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return False
    
    print(f"🧪 Testing audio chunking with database integration: {audio_path}")
    
    # Get file size
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"📁 File size: {file_size_mb:.1f} MB")
    
    # Initialize services
    try:
        settings = Settings()
        db = Supa()
        print("✅ Database connection initialized")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False
    
    # Create a test audio record (matching audios table schema)
    audio_record = {
        "id": "test-audio-chunking-123",
        "run_id": "test-run-chunking-123", 
        "location_id": "test-location-chunking-123",
        "date": "2025-01-08",
        "started_at": "2025-01-08T10:00:00Z",
        "ended_at": "2025-01-08T18:00:00Z",
        "link": "test/audio/chunking_test.mp3",
        "status": "processing"
    }
    
    # Monitor memory before processing
    initial_memory = get_memory_usage()
    print(f"📊 Initial memory: {initial_memory:.1f} MB")
    
    start_time = time.time()
    
    try:
        # Run the chunked transcription with database integration
        segments = transcribe_audio(audio_path, db=db, audio_record=audio_record)
        
        end_time = time.time()
        final_memory = get_memory_usage()
        
        # Results
        print(f"\n🎉 Audio chunking test completed successfully!")
        print(f"⏱️  Processing time: {end_time - start_time:.1f} seconds")
        print(f"📊 Memory usage: {initial_memory:.1f} MB → {final_memory:.1f} MB")
        print(f"📈 Memory efficiency: {((final_memory - initial_memory) / initial_memory * 100):+.1f}%")
        print(f"📝 Segments transcribed: {len(segments)}")
        
        # Show sample segments
        if segments:
            print(f"\n📄 Sample segments:")
            for i, segment in enumerate(segments[:3]):  # Show first 3 segments
                print(f"  {i+1}. [{segment['start']:.1f}s - {segment['end']:.1f}s]: {segment['text'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_chunking(audio_path: str):
    """
    Test simple chunking without database integration.
    """
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return False
    
    print(f"🧪 Testing simple chunking (no database): {audio_path}")
    
    # Get file size
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"📁 File size: {file_size_mb:.1f} MB")
    
    # Monitor memory before processing
    initial_memory = get_memory_usage()
    print(f"📊 Initial memory: {initial_memory:.1f} MB")
    
    start_time = time.time()
    
    try:
        # Run the chunked transcription without database
        segments = transcribe_audio(audio_path)
        
        end_time = time.time()
        final_memory = get_memory_usage()
        
        # Results
        print(f"\n🎉 Simple chunking test completed successfully!")
        print(f"⏱️  Processing time: {end_time - start_time:.1f} seconds")
        print(f"📊 Memory usage: {initial_memory:.1f} MB → {final_memory:.1f} MB")
        print(f"📈 Memory efficiency: {((final_memory - initial_memory) / initial_memory * 100):+.1f}%")
        print(f"📝 Segments transcribed: {len(segments)}")
        
        # Show sample segments
        if segments:
            print(f"\n📄 Sample segments:")
            for i, segment in enumerate(segments[:3]):  # Show first 3 segments
                print(f"  {i+1}. [{segment['start']:.1f}s - {segment['end']:.1f}s]: {segment['text'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("Usage: python test_audio_chunking.py <audio_file_path> [test_type]")
        print("Example: python test_audio_chunking.py /path/to/audio.mp3 simple")
        print("Example: python test_audio_chunking.py /path/to/audio.mp3 full")
        print("")
        print("Test types:")
        print("  simple - Test chunking without database integration")
        print("  full   - Test chunking with database integration (default)")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    test_type = sys.argv[2] if len(sys.argv) > 2 else "full"
    
    print(f"🚀 Starting audio chunking test")
    print(f"📄 Audio file: {audio_path}")
    print(f"🧪 Test type: {test_type}")
    print("")
    
    if test_type == "simple":
        success = test_simple_chunking(audio_path)
    else:
        success = test_audio_chunking_with_db(audio_path)
    
    if success:
        print("\n✅ Audio chunking test passed!")
        sys.exit(0)
    else:
        print("\n❌ Audio chunking test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
