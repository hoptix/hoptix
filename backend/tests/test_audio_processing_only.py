#!/usr/bin/env python3
"""
Test only the audio processing part with the downloaded audio file
"""
import sys
import os
import shutil

# Add the backend directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.audio import AudioTransactionProcessor

def test_audio_processing():
    """Test audio processing with the downloaded audio file"""
    print("🧪 Testing Audio Processing Only...")
    
    # Use the downloaded audio file from the logs
    audio_path = "/var/folders/y2/zmhv5c3s18d1_61d170dzx1c0000gn/T/tmputwq90hr.mp3"
    
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return False
    
    print(f"✅ Using audio file: {audio_path}")
    print(f"📊 File size: {os.path.getsize(audio_path) / (1024*1024):.1f} MB")
    
    try:
        # Test audio processing
        audio_processor = AudioTransactionProcessor()
        location_id = "19f4e061-786c-4500-baba-d561cd0dd7f8"
        original_filename = "audio_2025-10-10_10-00-02.mp3"
        output_dir = "test_extracted_audio"
        
        print(f"🎵 Processing audio file...")
        print(f"📍 Location ID: {location_id}")
        print(f"📁 Output directory: {output_dir}")
        print(f"📄 Original filename: {original_filename}")
        
        clip_paths, begin_times, end_times, reg_begin_times, reg_end_times = audio_processor.create_audio_subclips(
            audio_path, location_id, output_dir, original_filename
        )
        
        print(f"\n📊 RESULTS:")
        print(f"✅ Total clips created: {len(clip_paths)}")
        print(f"✅ Successful clips: {len([p for p in clip_paths if p])}")
        print(f"✅ Begin times: {len(begin_times)}")
        print(f"✅ End times: {len(end_times)}")
        print(f"✅ Regularized begin times: {len(reg_begin_times)}")
        print(f"✅ Regularized end times: {len(reg_end_times)}")
        
        # Show first few clip details
        if clip_paths:
            print(f"\n📋 FIRST 5 CLIPS:")
            for i, (clip_path, begin, end, reg_begin, reg_end) in enumerate(zip(
                clip_paths[:5], begin_times[:5], end_times[:5], 
                reg_begin_times[:5], reg_end_times[:5]
            )):
                if clip_path:
                    duration = end - begin
                    print(f"  {i+1}. {os.path.basename(clip_path)}")
                    print(f"     Duration: {duration:.1f}s")
                    print(f"     Time: {reg_begin} - {reg_end}")
                    print(f"     Size: {os.path.getsize(clip_path) / 1024:.1f} KB")
                else:
                    print(f"  {i+1}. [FAILED CLIP]")
        
        # Check if timestamps are correct (should show 2025-10-10, not 2025-10-14)
        if reg_begin_times:
            print(f"\n🕐 TIMESTAMP CHECK:")
            print(f"First clip timestamp: {reg_begin_times[0]}")
            if "2025_10_10" in str(reg_begin_times[0]) or "10:00" in str(reg_begin_times[0]):
                print("✅ Timestamps appear to be using correct date (2025-10-10)")
            else:
                print("⚠️ Timestamps might be using wrong date")
        
        # Clean up test directory
        if os.path.exists(output_dir):
            print(f"\n🧹 Cleaning up test directory: {output_dir}")
            shutil.rmtree(output_dir)
            print("✅ Cleaned up test directory")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Audio Processing Test...")
    print("="*60)
    
    success = test_audio_processing()
    
    print("\n" + "="*60)
    if success:
        print("🎉 Audio processing test PASSED!")
        exit(0)
    else:
        print("❌ Audio processing test FAILED!")
        exit(1)
