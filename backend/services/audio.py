import os
import numpy as np
import soundfile as sf
from datetime import datetime
from typing import List, Tuple
from moviepy.editor import AudioFileClip

class AudioTransactionProcessor:
    """Process audio files to extract individual transactions using silence detection"""
    
    def __init__(self):
        # Audio processing constants
        self.AUDIO_SAMPLE_RATE = 44100
        self.SILENCE_INTERVAL = 15  # seconds
        self.TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
        
    def create_audio_subclips(self, audio_path: str, location_id: str, 
                            output_dir: str = "extracted_audio") -> Tuple[List[str], List[float], List[float], List[str], List[str]]:
        """
        Create audio subclips from audio file using silence detection (adapted from create_subclips)
        
        Args:
            audio_path: Path to the audio file (MP3, WAV, etc.)
            location_id: Location identifier
            output_dir: Directory to save audio clips
            
        Returns:
            Tuple of (audio_clip_paths, begin_times, end_times, reg_begin_times, reg_end_times)
        """
        print(f'🎵 Processing audio file: {audio_path}')
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Load audio file using AudioFileClip (streaming, memory efficient)
        print('📊 Loading audio file with AudioFileClip...')
        try:
            # Disable MoviePy logging to avoid stdout issues
            import logging
            logging.getLogger("moviepy").setLevel(logging.ERROR)
            
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            sr = audio_clip.fps
            print(f'📊 Audio loaded: {duration:.1f}s duration, {sr}Hz sample rate')
        except Exception as e:
            print(f'❌ Failed to load audio file with AudioFileClip: {e}')
            print('🔄 Falling back to soundfile approach...')
            return self._fallback_processing(audio_path, location_id, output_dir)
        
        # Detect transaction boundaries using streaming approach
        print('🔍 Detecting transaction boundaries using streaming silence detection...')
        trans_begin, trans_end = self._detect_transaction_boundaries_streaming(audio_clip, sr)
        
        print(f'✅ Found {len(trans_begin)} transactions')
        print(f'🔍 Begin times: {trans_begin}')
        print(f'🔍 End times: {trans_end}')
        
        if not trans_begin:
            print('⚠️ No transactions detected in audio file')
            return [], [], [], [], []
        
        # Ensure we have matching begin/end times
        if len(trans_begin) != len(trans_end):
            trans_end.append(duration)
            print(f'🔍 Adjusted end times to match begin times')
        
        # Generate regularized timestamps
        print('🕐 Generating regularized timestamps...')
        trans_reg_begin = [self._convert_timestamp_to_hhmmss(t, audio_path) for t in trans_begin]
        trans_reg_end = [self._convert_timestamp_to_hhmmss(t, audio_path) for t in trans_end]
        
        # Create audio clips
        print('✂️ Creating audio clips...')
        audio_clip_paths = []
        
        for i, (begin_time, end_time) in enumerate(zip(trans_begin, trans_end)):
            try:
                # Generate unique filename
                clip_filename = self._generate_clip_filename(
                    location_id, audio_path, trans_reg_begin[i], i
                )
                clip_path = os.path.join(output_dir, clip_filename)
                
                # Extract audio segment using AudioFileClip
                self._extract_audio_segment_streaming(audio_clip, clip_path, begin_time, end_time)
                
                # Verify clip was created successfully
                if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                    audio_clip_paths.append(clip_path)
                    print(f'✅ Created audio clip {i+1}/{len(trans_begin)}: {clip_filename}')
                else:
                    print(f'❌ Failed to create audio clip {i+1}: {clip_filename}')
                    audio_clip_paths.append("")
                    
            except Exception as e:
                print(f'❌ Error creating audio clip {i+1}: {e}')
                audio_clip_paths.append("")
        
        # Clean up main audio clip to free memory
        audio_clip.close()
        
        print(f'🎉 Audio processing completed: {len([p for p in audio_clip_paths if p])} clips created')
        return audio_clip_paths, trans_begin, trans_end, trans_reg_begin, trans_reg_end
    
    def _detect_transaction_boundaries_streaming(self, audio_clip: AudioFileClip, sr: int) -> Tuple[List[float], List[float]]:
        """
        Detect transaction boundaries using AudioFileClip streaming (memory efficient)
        Uses the same approach as the original video processing
        """
        trans_begin = []
        trans_end = []
        
        duration = audio_clip.duration
        print(f'🔍 Processing audio with {self.SILENCE_INTERVAL}s silence intervals')
        
        # Process in chunks to avoid memory issues
        chunk_duration = 60  # Process 1 minute at a time
        current_time = 0.0
        prev_state = 0  # 0 = silence, 1 = active
        
        try:
            while current_time < duration:
                # Extract 1-minute chunk
                chunk_end_time = min(current_time + chunk_duration, duration)
                chunk = audio_clip.subclip(current_time, chunk_end_time)
                
                # Get audio data for this chunk (with error handling)
                try:
                    chunk_data = chunk.to_soundarray()
                except Exception as e:
                    print(f'⚠️ Error getting audio data for chunk {current_time:.1f}s: {e}')
                    chunk.close()
                    current_time += chunk_duration
                    continue
                
                # Process chunk for silence detection
                chunk_begin, chunk_end, new_state = self._process_chunk_for_silence_streaming(
                    chunk_data, current_time, sr, prev_state
                )
                
                # Update transaction boundaries
                trans_begin.extend(chunk_begin)
                trans_end.extend(chunk_end)
                
                # Update state for next chunk
                prev_state = new_state
                
                # Clean up chunk to free memory
                chunk.close()
                
                current_time += chunk_duration
                
        except Exception as e:
            print(f'❌ Error in streaming silence detection: {e}')
            return [], []
        
        # Handle case where audio ends during active period
        if len(trans_begin) != len(trans_end):
            trans_end.append(duration)
        
        return trans_begin, trans_end
    
    def _process_chunk_for_silence_streaming(self, chunk_data: np.ndarray, chunk_start_time: float, 
                                           sr: int, prev_state: int) -> Tuple[List[float], List[float], int]:
        """
        Process a single chunk for silence detection using streaming approach
        """
        chunk_begin = []
        chunk_end = []
        
        interval_samples = int(self.SILENCE_INTERVAL * sr)
        
        if len(chunk_data) < interval_samples:
            return chunk_begin, chunk_end, prev_state
        
        index = 0
        current_state = prev_state
        
        while index + interval_samples < len(chunk_data):
            # Check if this interval is silent
            interval_avg = float(np.average(chunk_data[index:index + interval_samples]))
            current_time = chunk_start_time + (index / sr)
            
            if interval_avg == 0.0:  # Silent period
                if current_state == 1:  # Transition from active to silence
                    chunk_end.append(current_time)
                    current_state = 0
            else:  # Active period
                if current_state == 0:  # Transition from silence to active
                    chunk_begin.append(current_time)
                    current_state = 1
            
            index += interval_samples
        
        return chunk_begin, chunk_end, current_state
    
    def _convert_timestamp_to_hhmmss(self, seconds: float, audio_path: str) -> str:
        """
        Convert seconds to HH:MM:SS format based on audio file timestamp
        Adapted from convert_timestamp function
        """
        try:
            # Extract timestamp from filename (assuming format like original)
            # This might need adjustment based on your actual filename format
            filename = os.path.basename(audio_path)
            
            # Try to extract timestamp from filename
            # Assuming format like: location_YYYYMMDDHHMMSS.mp3
            if '_' in filename:
                timestamp_part = filename.split('_')[-1].split('.')[0]
                if len(timestamp_part) >= 14:  # YYYYMMDDHHMMSS
                    dt = datetime.strptime(timestamp_part[:14], self.TIMESTAMP_FORMAT)
                else:
                    # Fallback to current time
                    dt = datetime.now()
            else:
                # Fallback to current time
                dt = datetime.now()
            
            # Calculate absolute time
            year = dt.year
            month = dt.month
            day = dt.day
            hour = dt.hour
            minute = dt.minute
            second = dt.second
            
            seconds_elapsed = hour * 3600 + minute * 60 + second
            total_seconds = (seconds + seconds_elapsed) % (24 * 3600)
            
            hours = int(total_seconds // 3600)
            total_seconds %= 3600
            minutes = int(total_seconds // 60)
            total_seconds %= 60
            seconds = int(total_seconds)
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
        except Exception as e:
            print(f'⚠️ Error converting timestamp: {e}')
            # Fallback to simple seconds conversion
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _generate_clip_filename(self, location_id: str, audio_path: str, 
                              begin_timestamp: str, index: int) -> str:
        """
        Generate unique filename for audio clip
        Adapted from original naming logic
        """
        try:
            # Extract date from audio filename
            filename = os.path.basename(audio_path)
            if '_' in filename:
                timestamp_part = filename.split('_')[-1].split('.')[0]
                if len(timestamp_part) >= 8:  # At least YYYYMMDD
                    dt = datetime.strptime(timestamp_part[:8], "%Y%m%d")
                    year = dt.year
                    month = dt.month
                    day = dt.day
                else:
                    # Fallback to current date
                    now = datetime.now()
                    year = now.year
                    month = now.month
                    day = now.day
            else:
                # Fallback to current date
                now = datetime.now()
                year = now.year
                month = now.month
                day = now.day
            
            # Format: location_YYYY_MM_DD_HH_MM_SS.mp3
            name = f"{location_id}_{year}_{month}_{day}_{begin_timestamp[:2]}_{begin_timestamp[3:5]}_{begin_timestamp[6:8]}"
            return f"{name}.mp3"
            
        except Exception as e:
            print(f'⚠️ Error generating filename: {e}')
            # Fallback naming
            return f"{location_id}_clip_{index:03d}.mp3"
    
    def _extract_audio_segment_streaming(self, audio_clip: AudioFileClip, output_path: str, 
                                       start_time: float, end_time: float):
        """
        Extract audio segment using AudioFileClip (streaming, memory efficient)
        """
        try:
            # Extract subclip using AudioFileClip (same as original video processing)
            subclip = audio_clip.subclip(start_time, end_time)
            
            # Write to file
            subclip.write_audiofile(output_path, verbose=False, logger=None)
            
            # Clean up subclip to free memory
            subclip.close()
            
        except Exception as e:
            print(f'❌ Error extracting audio segment: {e}')
            raise e