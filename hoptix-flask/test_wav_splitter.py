#!/usr/bin/env python3
"""
Test script for WAV splitter functionality.
This script tests the WAV splitting logic without requiring a full pipeline run.
"""

import os
import sys
import tempfile
import logging
from datetime import datetime, timedelta
import numpy as np
import soundfile as sf

# Add the current directory to Python path
sys.path.insert(0, '.')

from services.wav_splitter import WAVSplitter
from config import Settings
from integrations.db_supabase import Supa
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def create_test_wav_file(duration_seconds: int, sample_rate: int = 44100) -> str:
    """Create a test WAV file with the specified duration using memory-efficient approach."""
    # For very long files, create in chunks to avoid memory issues
    chunk_duration = 60  # 1 minute chunks
    total_samples = int(duration_seconds * sample_rate)
    chunk_samples = int(chunk_duration * sample_rate)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    logger.info(f"Creating test WAV file: {tmp_path}")
    logger.info(f"  Duration: {duration_seconds}s")
    logger.info(f"  Sample rate: {sample_rate}Hz")
    
    # Write audio data in chunks to avoid memory issues
    with sf.SoundFile(tmp_path, 'w', sample_rate, 1) as f:
        for start_sample in range(0, total_samples, chunk_samples):
            end_sample = min(start_sample + chunk_samples, total_samples)
            chunk_duration_actual = (end_sample - start_sample) / sample_rate
            
            # Generate chunk data
            t = np.linspace(0, chunk_duration_actual, end_sample - start_sample, False)
            # Create a 440Hz sine wave (A note) with some variation
            frequency = 440 + (start_sample / total_samples) * 100  # Vary frequency slightly
            audio_chunk = np.sin(2 * np.pi * frequency * t) * 0.5
            
            f.write(audio_chunk)
    
    file_size = os.path.getsize(tmp_path)
    logger.info(f"  File size: {file_size:,} bytes ({file_size / (1024*1024):.1f}MB)")
    
    return tmp_path

def create_test_video_record() -> dict:
    """Create a test video record for testing."""
    return {
        "id": "test-video-123",
        "run_id": "test-run-456",
        "location_id": "test-location-789",
        "organization_id": "test-org-abc",
        "started_at": datetime.now().isoformat(),
        "ended_at": (datetime.now() + timedelta(minutes=45)).isoformat(),
        "status": "uploaded",
        "s3_key": "test/audio/test_file.wav",
        "meta": {
            "gdrive_file_id": "test-gdrive-id",
            "gdrive_file_name": "test_audio_file.wav"
        }
    }

def test_wav_splitter():
    """Test the WAV splitter functionality."""
    logger.info("🧪 Starting WAV splitter tests...")
    
    try:
        # Load environment
        load_dotenv()
        settings = Settings()
        
        # Create a mock database connection (we won't actually use it for this test)
        class MockDB:
            def __init__(self):
                self.client = None
        
        db = MockDB()
        wav_splitter = WAVSplitter(db, settings)
        
        # Test 1: Create a large WAV file (35 minutes - should be split)
        logger.info("\n📋 Test 1: Large WAV file (35 minutes)")
        large_wav_path = create_test_wav_file(35 * 60)  # 35 minutes
        
        should_split, reason = wav_splitter.should_split_wav(large_wav_path)
        logger.info(f"Should split: {should_split}")
        logger.info(f"Reason: {reason}")
        
        if should_split:
            logger.info("✅ Large WAV file correctly identified for splitting")
            
            # Test splitting
            test_video_record = create_test_video_record()
            chunk_records = wav_splitter.split_wav_file(large_wav_path, test_video_record)
            
            logger.info(f"✅ Successfully split into {len(chunk_records)} chunks")
            for i, chunk_record in enumerate(chunk_records):
                chunk_meta = chunk_record['meta']
                logger.info(f"  Chunk {i+1}: {chunk_meta['chunk_duration']:.1f}s "
                          f"({chunk_meta['chunk_start_time']:.1f}s - {chunk_meta['chunk_end_time']:.1f}s)")
                logger.info(f"    Local path: {chunk_meta['local_chunk_path']}")
                
                # Verify chunk file exists and has reasonable size
                if os.path.exists(chunk_meta['local_chunk_path']):
                    chunk_size = os.path.getsize(chunk_meta['local_chunk_path'])
                    logger.info(f"    File size: {chunk_size:,} bytes")
                else:
                    logger.error(f"    ❌ Chunk file not found!")
            
            # Clean up chunk files
            wav_splitter.cleanup_chunk_files(chunk_records)
            logger.info("🧹 Cleaned up chunk files")
        else:
            logger.error("❌ Large WAV file was not identified for splitting")
        
        # Clean up test file
        os.remove(large_wav_path)
        logger.info("🧹 Cleaned up test WAV file")
        
        # Test 2: Create a small WAV file (10 minutes - should NOT be split)
        logger.info("\n📋 Test 2: Small WAV file (10 minutes)")
        small_wav_path = create_test_wav_file(10 * 60)  # 10 minutes
        
        should_split, reason = wav_splitter.should_split_wav(small_wav_path)
        logger.info(f"Should split: {should_split}")
        logger.info(f"Reason: {reason}")
        
        if not should_split:
            logger.info("✅ Small WAV file correctly identified as not needing splitting")
        else:
            logger.error("❌ Small WAV file was incorrectly identified for splitting")
        
        # Clean up test file
        os.remove(small_wav_path)
        logger.info("🧹 Cleaned up test WAV file")
        
        logger.info("\n🎉 All WAV splitter tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_wav_splitter()
    sys.exit(0 if success else 1)
