#!/usr/bin/env python3
"""
Test script to compare sequential vs parallel chunked processing performance.
"""

import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_parallel_vs_sequential():
    """Test parallel vs sequential processing performance"""
    print("🧪 Testing Parallel vs Sequential Processing")
    print("=" * 60)
    
    # Test with a small audio file first
    test_audio_path = "/path/to/your/test/audio.mp3"  # Replace with actual path
    
    if not os.path.exists(test_audio_path):
        print("❌ Please provide a valid audio file path in the script")
        return
    
    print(f"📁 Testing with: {test_audio_path}")
    
    # Test sequential processing
    print("\n🔄 Testing Sequential Processing...")
    from config.chunked_processing import PARALLEL_CHUNKS, MAX_WORKERS
    
    # Temporarily disable parallel processing
    original_parallel = PARALLEL_CHUNKS
    PARALLEL_CHUNKS = False
    
    start_time = time.time()
    try:
        from services.transcribe import transcribe_audio
        segments_seq = transcribe_audio(test_audio_path)
        sequential_time = time.time() - start_time
        print(f"✅ Sequential processing completed in {sequential_time:.1f} seconds")
        print(f"📝 Segments: {len(segments_seq)}")
    except Exception as e:
        print(f"❌ Sequential processing failed: {e}")
        sequential_time = None
    
    # Test parallel processing
    print("\n🚀 Testing Parallel Processing...")
    PARALLEL_CHUNKS = True
    
    start_time = time.time()
    try:
        segments_par = transcribe_audio(test_audio_path)
        parallel_time = time.time() - start_time
        print(f"✅ Parallel processing completed in {parallel_time:.1f} seconds")
        print(f"📝 Segments: {len(segments_par)}")
    except Exception as e:
        print(f"❌ Parallel processing failed: {e}")
        parallel_time = None
    
    # Restore original setting
    PARALLEL_CHUNKS = original_parallel
    
    # Compare results
    if sequential_time and parallel_time:
        speedup = sequential_time / parallel_time
        print(f"\n📊 Performance Comparison:")
        print(f"   Sequential: {sequential_time:.1f} seconds")
        print(f"   Parallel:   {parallel_time:.1f} seconds")
        print(f"   Speedup:    {speedup:.1f}x faster")
        print(f"   Time saved: {sequential_time - parallel_time:.1f} seconds")
        
        if speedup > 1.5:
            print("🎉 Parallel processing shows significant improvement!")
        elif speedup > 1.1:
            print("✅ Parallel processing shows modest improvement")
        else:
            print("⚠️  Parallel processing shows minimal improvement")

if __name__ == "__main__":
    test_parallel_vs_sequential()
