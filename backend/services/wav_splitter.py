#!/usr/bin/env python3
"""
WAV/MP3 File Splitter Service for Backend

This service handles splitting large audio files into smaller chunks for parallel processing.
It creates separate video records for each chunk and manages the splitting process.
Supports both WAV and MP3 input files.
"""

import os
import tempfile
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import soundfile as sf
import numpy as np
from uuid import uuid4
import subprocess

logger = logging.getLogger(__name__)

class AudioSplitter:
    """Service for splitting large audio files into manageable chunks."""
    
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings
        
        # Configuration for splitting
        self.max_file_size_mb = 50  # Split files larger than 50MB
        self.max_duration_minutes = 30  # Split files longer than 30 minutes
        self.chunk_duration_minutes = 20  # Each chunk should be ~20 minutes
        self.overlap_seconds = 5  # 5 second overlap between chunks to avoid cutting mid-sentence
        
    def should_split_audio(self, audio_path: str) -> Tuple[bool, str]:
        """
        Determine if an audio file should be split based on size and duration.
        
        Returns:
            Tuple[bool, str]: (should_split, reason)
        """
        print(f"🔍 DEBUG: should_split_audio called for: {audio_path}")
        print(f"🔍 DEBUG: File exists: {os.path.exists(audio_path)}")
        
        if not os.path.exists(audio_path):
            print(f"🔍 DEBUG: File does not exist, returning False")
            return False, "File does not exist"
            
        # Check file size
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"🔍 DEBUG: File size: {file_size_mb:.1f}MB, limit: {self.max_file_size_mb}MB")
        
        if file_size_mb > self.max_file_size_mb:
            print(f"🔍 DEBUG: File size exceeds limit, should split")
            return True, f"File size ({file_size_mb:.1f}MB) exceeds limit ({self.max_file_size_mb}MB)"
            
        # Check duration using ffprobe (works for both WAV and MP3)
        try:
            duration_seconds = self._get_audio_duration(audio_path)
            duration_minutes = duration_seconds / 60.0
            print(f"🔍 DEBUG: Duration: {duration_minutes:.1f}min, limit: {self.max_duration_minutes}min")
            
            if duration_minutes > self.max_duration_minutes:
                print(f"🔍 DEBUG: Duration exceeds limit, should split")
                return True, f"Duration ({duration_minutes:.1f}min) exceeds limit ({self.max_duration_minutes}min)"
                
        except Exception as e:
            logger.warning(f"Could not determine duration for {audio_path}: {e}")
            print(f"🔍 DEBUG: Duration check failed: {e}")
            # If we can't determine duration, split based on size only
            should_split = file_size_mb > self.max_file_size_mb
            print(f"🔍 DEBUG: Fallback to size-based decision: {should_split}")
            return should_split, f"Could not determine duration, splitting based on size"
            
        print(f"🔍 DEBUG: File is within limits, no splitting needed")
        return False, "File is within size and duration limits"
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio file duration using ffprobe (works for WAV, MP3, etc.)"""
        try:
            out = subprocess.check_output([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1",
                audio_path
            ])
            return float(out.decode().strip())
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0
    
    def split_audio_file(self, audio_path: str, original_audio_row: Dict) -> List[Dict]:
        """
        Split a large audio file into smaller chunks and create audio records for each chunk.
        Uses memory-efficient approach to avoid loading entire file into RAM.
        
        Args:
            audio_path: Path to the original audio file (WAV or MP3)
            original_audio_row: Original audio record from database
            
        Returns:
            List[Dict]: List of new audio records for each chunk
        """
        logger.info(f"🔪 Starting audio file splitting for: {os.path.basename(audio_path)}")
        print(f"🔍 DEBUG: split_audio_file called with audio_path: {audio_path}")
        print(f"🔍 DEBUG: original_audio_row keys: {list(original_audio_row.keys()) if original_audio_row else 'None'}")
        
        # Get file info using ffprobe (works for any audio format)
        try:
            duration_seconds = self._get_audio_duration(audio_path)
            logger.info(f"📊 Original file: {duration_seconds:.1f}s duration")
            print(f"🔍 DEBUG: Audio duration: {duration_seconds:.1f} seconds")
        except Exception as e:
            logger.error(f"❌ Failed to analyze audio file {audio_path}: {e}")
            print(f"🔍 DEBUG: Duration analysis failed: {e}")
            raise
            
        # Calculate chunk parameters
        chunk_duration_seconds = self.chunk_duration_minutes * 60
        overlap_seconds = self.overlap_seconds
        print(f"🔍 DEBUG: chunk_duration_seconds: {chunk_duration_seconds}, overlap_seconds: {overlap_seconds}")
        
        # Calculate number of chunks needed
        num_chunks = int(np.ceil(duration_seconds / (chunk_duration_seconds - overlap_seconds)))
        print(f"🔍 DEBUG: Calculated num_chunks: {num_chunks}")
        
        logger.info(f"📏 Splitting into {num_chunks} chunks of ~{self.chunk_duration_minutes}min each")
        
        # Create chunks using ffmpeg (works for any audio format)
        chunk_audio_records = []
        base_filename = os.path.splitext(os.path.basename(audio_path))[0]
        
        for i in range(num_chunks):
            print(f"🔍 DEBUG: Processing chunk {i+1}/{num_chunks}")
            
            # Calculate chunk boundaries in seconds with overlap
            start_time = i * (chunk_duration_seconds - overlap_seconds)
            end_time = min(start_time + chunk_duration_seconds, duration_seconds)
            print(f"🔍 DEBUG: Initial boundaries: {start_time:.1f}s - {end_time:.1f}s")
            
            # Ensure we don't go beyond the file
            if start_time >= duration_seconds:
                print(f"🔍 DEBUG: Start time {start_time} >= duration {duration_seconds}, breaking")
                break
            
            # For chunks after the first, add overlap at the beginning
            if i > 0:
                start_time = max(0, start_time - overlap_seconds)
                logger.info(f"🎵 Creating chunk {i+1}/{num_chunks}: {start_time:.1f}s - {end_time:.1f}s (with {overlap_seconds}s overlap)")
                print(f"🔍 DEBUG: Adjusted start_time with overlap: {start_time:.1f}s")
            else:
                logger.info(f"🎵 Creating chunk {i+1}/{num_chunks}: {start_time:.1f}s - {end_time:.1f}s")
                print(f"🔍 DEBUG: First chunk, no overlap adjustment")
            
            # Create temporary file for this chunk
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                chunk_path = tmp_file.name
                print(f"🔍 DEBUG: Created temp file: {chunk_path}")
                
            try:
                # Extract chunk using ffmpeg (converts to WAV for consistency)
                print(f"🔍 DEBUG: Calling _extract_chunk_with_ffmpeg")
                self._extract_chunk_with_ffmpeg(audio_path, chunk_path, start_time, end_time)
                chunk_size = os.path.getsize(chunk_path)
                print(f"🔍 DEBUG: Chunk file created, size: {chunk_size:,} bytes")
                
                logger.info(f"💾 Chunk {i+1} saved: {chunk_path} ({chunk_size:,} bytes)")
                
                # Create audio record for this chunk
                print(f"🔍 DEBUG: Creating audio record for chunk {i+1}")
                chunk_audio_record = self._create_chunk_audio_record(
                    original_audio_row, 
                    i + 1, 
                    num_chunks,
                    start_time,
                    end_time,
                    chunk_path,
                    chunk_size,
                    overlap_seconds if i > 0 else 0  # Pass overlap info
                )
                print(f"🔍 DEBUG: Created audio record with id: {chunk_audio_record.get('id')}")
                
                chunk_audio_records.append(chunk_audio_record)
                print(f"🔍 DEBUG: Added chunk record to list. Total records: {len(chunk_audio_records)}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create chunk {i+1}: {e}")
                print(f"🔍 DEBUG: Chunk creation failed: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                # Clean up failed chunk file
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    print(f"🔍 DEBUG: Cleaned up failed chunk file: {chunk_path}")
                continue
            
        logger.info(f"✅ Successfully created {len(chunk_audio_records)} audio chunks")
        return chunk_audio_records
    
    def _extract_chunk_with_ffmpeg(self, input_path: str, output_path: str, start_time: float, end_time: float):
        """Extract audio chunk using ffmpeg (works for any audio format)"""
        duration = end_time - start_time
        cmd = [
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "error",
            "-ss", f"{start_time:.3f}",
            "-i", input_path,
            "-t", f"{duration:.3f}",
            "-vn",  # no video
            "-acodec", "pcm_s16le",  # WAV PCM 16-bit
            "-ar", "16000",  # 16 kHz sample rate
            "-ac", "1",  # mono
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    def _create_chunk_audio_record(self, original_row: Dict, chunk_num: int, total_chunks: int, 
                                 start_time: float, end_time: float, chunk_path: str, chunk_size: int, overlap_seconds: float = 0) -> Dict:
        """Create an audio record for an audio chunk."""
        
        # Generate unique ID for this chunk
        chunk_id = str(uuid4())
        
        # Calculate chunk-specific timestamps
        original_start = datetime.fromisoformat(original_row["started_at"].replace('Z', '+00:00'))
        chunk_start = original_start + timedelta(seconds=start_time)
        chunk_end = original_start + timedelta(seconds=end_time)
        
        # Create link for this chunk (make it unique using chunk_id)
        original_link = original_row.get("link", "")
        if original_link:
            base_link = os.path.splitext(original_link)[0]
            chunk_link = f"{base_link}_chunk_{chunk_id}.wav"
        else:
            chunk_link = f"audio_processing/{original_row['run_id']}/chunk_{chunk_id}.wav"
        
        # Create metadata for this chunk
        chunk_meta = {
            "is_chunk": True,
            "chunk_number": chunk_num,
            "total_chunks": total_chunks,
            "original_audio_id": original_row["id"],
            "chunk_start_time": start_time,
            "chunk_end_time": end_time,
            "chunk_duration": end_time - start_time,
            "local_chunk_path": chunk_path,
            "chunk_size_bytes": chunk_size,
            "overlap_seconds": overlap_seconds,
            "has_overlap": overlap_seconds > 0
        }
        
        # Create the audio record (matching audios table schema)
        chunk_audio_record = {
            "id": chunk_id,
            "run_id": original_row["run_id"],
            "location_id": original_row["location_id"],
            "date": original_row["date"],
            "started_at": chunk_start.isoformat(),
            "ended_at": chunk_end.isoformat(),
            "link": chunk_link,
            "status": "uploaded",  # Ready for processing
            "meta": chunk_meta
        }
        
        logger.info(f"📝 Created audio record for chunk {chunk_num}: {chunk_id}")
        return chunk_audio_record
    
    def insert_chunk_audio_records(self, chunk_audio_records: List[Dict]) -> List[str]:
        """
        Insert chunk audio records into the database.
        
        Args:
            chunk_audio_records: List of audio records for chunks
            
        Returns:
            List[str]: List of inserted audio IDs
        """
        try:
            logger.info(f"💾 Inserting {len(chunk_audio_records)} chunk audio records into database")
            
            if not chunk_audio_records:
                logger.warning("No chunk audio records to insert")
                return []
            
            # Upsert all chunk records (handle duplicates gracefully)
            result = self.db.client.table("audios").upsert(chunk_audio_records, on_conflict="id").execute()
            
            if result.data:
                chunk_ids = [record["id"] for record in result.data]
                logger.info(f"✅ Successfully inserted {len(chunk_ids)} chunk audio records")
                return chunk_ids
            else:
                logger.error("❌ No data returned from chunk audio record insertion")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to insert chunk audio records: {e}")
            return []
    
    def cleanup_chunk_files(self, chunk_audio_records: List[Dict]):
        """Clean up temporary chunk files."""
        for record in chunk_audio_records:
            chunk_path = record["meta"].get("local_chunk_path")
            if chunk_path and os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                    logger.info(f"🗑️ Cleaned up chunk file: {chunk_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not clean up chunk file {chunk_path}: {e}")
    
    def process_large_audio_file(self, audio_path: str, original_audio_row: Dict) -> List[Dict]:
        """
        Complete process for handling a large audio file:
        1. Split into chunks
        2. Create audio records for chunks (with local file paths)
        3. Insert audio records into database
        
        Args:
            audio_path: Path to the original audio file
            original_audio_row: Original audio record
            
        Returns:
            List[Dict]: List of chunk audio records with local file paths
        """
        logger.info(f"🚀 Processing large audio file: {os.path.basename(audio_path)}")
        
        try:
            # Step 1: Split the audio file
            chunk_audio_records = self.split_audio_file(audio_path, original_audio_row)
            
            # Step 2: Insert audio records into database
            chunk_ids = self.insert_chunk_audio_records(chunk_audio_records)
            
            if not chunk_ids:
                logger.error("❌ Failed to insert chunk audio records")
                self.cleanup_chunk_files(chunk_audio_records)
                return []
            
            logger.info(f"✅ Successfully processed large audio file into {len(chunk_ids)} chunks")
            logger.info("📝 Chunk files will be cleaned up after processing by workers")
            return chunk_audio_records
            
        except Exception as e:
            logger.error(f"❌ Failed to process large audio file: {e}")
            # Clean up any temporary files
            if 'chunk_audio_records' in locals():
                self.cleanup_chunk_files(chunk_audio_records)
            return []
