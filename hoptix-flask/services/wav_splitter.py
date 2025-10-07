#!/usr/bin/env python3
"""
WAV File Splitter Service

This service handles splitting large WAV files into smaller chunks for parallel processing.
It creates separate video records for each chunk and manages the splitting process.
"""

import os
import tempfile
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import librosa
import soundfile as sf
import numpy as np
from uuid import uuid4

logger = logging.getLogger(__name__)

class WAVSplitter:
    """Service for splitting large WAV files into manageable chunks."""
    
    def __init__(self, db, settings):
        self.db = db
        self.settings = settings
        
        # Configuration for splitting
        self.max_file_size_mb = 50  # Split files larger than 50MB
        self.max_duration_minutes = 30  # Split files longer than 30 minutes
        self.chunk_duration_minutes = 20  # Each chunk should be ~20 minutes
        self.overlap_seconds = 5  # 5 second overlap between chunks to avoid cutting mid-sentence
        
    def should_split_wav(self, wav_path: str) -> Tuple[bool, str]:
        """
        Determine if a WAV file should be split based on size and duration.
        
        Returns:
            Tuple[bool, str]: (should_split, reason)
        """
        if not os.path.exists(wav_path):
            return False, "File does not exist"
            
        # Check file size
        file_size_mb = os.path.getsize(wav_path) / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            return True, f"File size ({file_size_mb:.1f}MB) exceeds limit ({self.max_file_size_mb}MB)"
            
        # Check duration
        try:
            y, sr = librosa.load(wav_path, sr=None)
            duration_seconds = len(y) / float(sr)
            duration_minutes = duration_seconds / 60.0
            
            if duration_minutes > self.max_duration_minutes:
                return True, f"Duration ({duration_minutes:.1f}min) exceeds limit ({self.max_duration_minutes}min)"
                
        except Exception as e:
            logger.warning(f"Could not determine duration for {wav_path}: {e}")
            # If we can't determine duration, split based on size only
            return file_size_mb > self.max_file_size_mb, f"Could not determine duration, splitting based on size"
            
        return False, "File is within size and duration limits"
    
    def split_wav_file(self, wav_path: str, original_video_row: Dict) -> List[Dict]:
        """
        Split a large WAV file into smaller chunks and create video records for each chunk.
        
        Args:
            wav_path: Path to the original WAV file
            original_video_row: Original video record from database
            
        Returns:
            List[Dict]: List of new video records for each chunk
        """
        logger.info(f"🔪 Starting WAV file splitting for: {os.path.basename(wav_path)}")
        
        # Load the WAV file
        try:
            y, sr = librosa.load(wav_path, sr=None)
            duration_seconds = len(y) / float(sr)
            logger.info(f"📊 Original file: {duration_seconds:.1f}s duration, {len(y)} samples at {sr}Hz")
        except Exception as e:
            logger.error(f"❌ Failed to load WAV file {wav_path}: {e}")
            raise
            
        # Calculate chunk parameters
        chunk_duration_seconds = self.chunk_duration_minutes * 60
        overlap_samples = int(self.overlap_seconds * sr)
        chunk_samples = int(chunk_duration_seconds * sr)
        
        # Calculate number of chunks needed
        total_samples = len(y)
        num_chunks = int(np.ceil(total_samples / (chunk_samples - overlap_samples)))
        
        logger.info(f"📏 Splitting into {num_chunks} chunks of ~{self.chunk_duration_minutes}min each")
        
        # Create chunks
        chunk_video_records = []
        base_filename = os.path.splitext(os.path.basename(wav_path))[0]
        
        for i in range(num_chunks):
            # Calculate chunk boundaries
            start_sample = i * (chunk_samples - overlap_samples)
            end_sample = min(start_sample + chunk_samples, total_samples)
            
            # Ensure we don't go beyond the file
            if start_sample >= total_samples:
                break
                
            start_time_seconds = start_sample / sr
            end_time_seconds = end_sample / sr
            
            logger.info(f"🎵 Creating chunk {i+1}/{num_chunks}: {start_time_seconds:.1f}s - {end_time_seconds:.1f}s")
            
            # Extract chunk audio
            chunk_audio = y[start_sample:end_sample]
            
            # Create temporary file for this chunk
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                chunk_path = tmp_file.name
                
            # Save chunk to temporary file
            sf.write(chunk_path, chunk_audio, sr)
            chunk_size = os.path.getsize(chunk_path)
            
            logger.info(f"💾 Chunk {i+1} saved: {chunk_path} ({chunk_size:,} bytes)")
            
            # Create video record for this chunk
            chunk_video_record = self._create_chunk_video_record(
                original_video_row, 
                i + 1, 
                num_chunks,
                start_time_seconds,
                end_time_seconds,
                chunk_path,
                chunk_size
            )
            
            chunk_video_records.append(chunk_video_record)
            
        logger.info(f"✅ Successfully created {len(chunk_video_records)} WAV chunks")
        return chunk_video_records
    
    def _create_chunk_video_record(self, original_row: Dict, chunk_num: int, total_chunks: int, 
                                 start_time: float, end_time: float, chunk_path: str, chunk_size: int) -> Dict:
        """Create a video record for a WAV chunk."""
        
        # Generate unique ID for this chunk
        chunk_id = str(uuid4())
        
        # Calculate chunk-specific timestamps
        original_start = datetime.fromisoformat(original_row["started_at"].replace('Z', '+00:00'))
        chunk_start = original_start + timedelta(seconds=start_time)
        chunk_end = original_start + timedelta(seconds=end_time)
        
        # Create S3 key for this chunk
        original_s3_key = original_row.get("s3_key", "")
        base_s3_key = os.path.splitext(original_s3_key)[0] if original_s3_key else f"chunk_{chunk_id}"
        chunk_s3_key = f"{base_s3_key}_chunk_{chunk_num:03d}.wav"
        
        # Create metadata for this chunk
        original_meta = original_row.get("meta", {})
        chunk_meta = original_meta.copy()
        chunk_meta.update({
            "is_chunk": True,
            "chunk_number": chunk_num,
            "total_chunks": total_chunks,
            "original_video_id": original_row["id"],
            "chunk_start_time": start_time,
            "chunk_end_time": end_time,
            "chunk_duration": end_time - start_time,
            "local_chunk_path": chunk_path,
            "chunk_size_bytes": chunk_size
        })
        
        # Create the video record
        chunk_video_record = {
            "id": chunk_id,
            "run_id": original_row["run_id"],
            "location_id": original_row["location_id"],
            "organization_id": original_row["organization_id"],
            "started_at": chunk_start.isoformat(),
            "ended_at": chunk_end.isoformat(),
            "status": "uploaded",  # Ready for processing
            "s3_key": chunk_s3_key,
            "meta": chunk_meta,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"📝 Created video record for chunk {chunk_num}: {chunk_id}")
        return chunk_video_record
    
    def upload_chunk_to_s3(self, chunk_video_record: Dict) -> bool:
        """
        Upload a WAV chunk to S3.
        
        Args:
            chunk_video_record: Video record containing chunk metadata
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            from integrations.s3_client import get_s3
            s3 = get_s3(self.settings.AWS_REGION)
            
            chunk_path = chunk_video_record["meta"]["local_chunk_path"]
            s3_key = chunk_video_record["s3_key"]
            
            logger.info(f"☁️ Uploading chunk to S3: {s3_key}")
            
            # Upload the chunk file
            with open(chunk_path, 'rb') as f:
                s3.put_object(
                    Bucket=self.settings.MEDIA_BUCKET,
                    Key=s3_key,
                    Body=f,
                    ContentType='audio/wav'
                )
            
            logger.info(f"✅ Chunk uploaded successfully: s3://{self.settings.MEDIA_BUCKET}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload chunk to S3: {e}")
            return False
    
    def insert_chunk_video_records(self, chunk_video_records: List[Dict]) -> List[str]:
        """
        Insert chunk video records into the database.
        
        Args:
            chunk_video_records: List of video records for chunks
            
        Returns:
            List[str]: List of inserted video IDs
        """
        try:
            logger.info(f"💾 Inserting {len(chunk_video_records)} chunk video records into database")
            
            # Insert all chunk records
            result = self.db.client.table("videos").insert(chunk_video_records).execute()
            
            if result.data:
                chunk_ids = [record["id"] for record in result.data]
                logger.info(f"✅ Successfully inserted {len(chunk_ids)} chunk video records")
                return chunk_ids
            else:
                logger.error("❌ No data returned from chunk video record insertion")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to insert chunk video records: {e}")
            return []
    
    def cleanup_chunk_files(self, chunk_video_records: List[Dict]):
        """Clean up temporary chunk files."""
        for record in chunk_video_records:
            chunk_path = record["meta"].get("local_chunk_path")
            if chunk_path and os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                    logger.info(f"🗑️ Cleaned up chunk file: {chunk_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not clean up chunk file {chunk_path}: {e}")
    
    def process_large_wav_file(self, wav_path: str, original_video_row: Dict) -> List[Dict]:
        """
        Complete process for handling a large WAV file:
        1. Split into chunks
        2. Create video records for chunks (with local file paths)
        3. Insert video records into database
        
        Args:
            wav_path: Path to the original WAV file
            original_video_row: Original video record
            
        Returns:
            List[Dict]: List of chunk video records with local file paths
        """
        logger.info(f"🚀 Processing large WAV file: {os.path.basename(wav_path)}")
        
        try:
            # Step 1: Split the WAV file
            chunk_video_records = self.split_wav_file(wav_path, original_video_row)
            
            # Step 2: Insert video records into database
            chunk_ids = self.insert_chunk_video_records(chunk_video_records)
            
            if not chunk_ids:
                logger.error("❌ Failed to insert chunk video records")
                self.cleanup_chunk_files(chunk_video_records)
                return []
            
            logger.info(f"✅ Successfully processed large WAV file into {len(chunk_ids)} chunks")
            return chunk_video_records
            
        except Exception as e:
            logger.error(f"❌ Failed to process large WAV file: {e}")
            # Clean up any temporary files
            if 'chunk_video_records' in locals():
                self.cleanup_chunk_files(chunk_video_records)
            return []
