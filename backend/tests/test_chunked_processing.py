#!/usr/bin/env python3
"""
Test script for the new chunked audio processing approach.
This script tests the memory-efficient transcription without running the full pipeline.
"""

import sys
import os
# Add the parent directory to the path so we can import from services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psutil
import time
from services.transcribe import transcribe_audio, get_memory_usage

def test_chunked_processing(audio_path: str):
    """
    Test the chunked processing approach with memory monitoring.
    """
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return False
    
    print(f"🧪 Testing chunked processing with: {audio_path}")
    
    # Get file size
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"📁 File size: {file_size_mb:.1f} MB")
    
    # Monitor memory before processing
    initial_memory = get_memory_usage()
    print(f"📊 Initial memory: {initial_memory:.1f} MB")
    
    start_time = time.time()
    
    try:
        # Run the chunked transcription (without db/audio_record for simple test)
        segments = transcribe_audio(audio_path)
        
        end_time = time.time()
        final_memory = get_memory_usage()
        
        # Results
        print(f"\n🎉 Test completed successfully!")
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
        return False

def main():
    """Main test function"""
    if len(sys.argv) != 2:
        print("Usage: python test_chunked_processing.py <audio_file_path>")
        print("Example: python test_chunked_processing.py /path/to/audio.mp3")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    success = test_chunked_processing(audio_path)
    
    if success:
        print("\n✅ Chunked processing test passed!")
        sys.exit(0)
    else:
        print("\n❌ Chunked processing test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
