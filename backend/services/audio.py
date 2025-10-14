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
        self.SILENCE_INTERVAL = 7  # seconds - much shorter for drive-thru transactions
        self.TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
        
    def create_audio_subclips(self, audio_path: str, location_id: str, 
                            output_dir: str = "extracted_audio", original_filename: str = None) -> Tuple[List[str], List[float], List[float], List[str], List[str]]:
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
            return self._fallback_processing(audio_path, location_id, output_dir, original_filename)
        
        # Detect transaction boundaries using streaming approach
        print('🔍 Detecting transaction boundaries using streaming silence detection...')
        trans_begin, trans_end = self._detect_transaction_boundaries_streaming(audio_clip, sr, audio_path, location_id, output_dir)
        
        # If streaming detection failed (empty results), fall back to soundfile approach
        if not trans_begin:
            print('⚠️ Streaming detection failed, falling back to soundfile approach...')
            audio_clip.close()
            return self._fallback_processing(audio_path, location_id, output_dir, original_filename)
        
        print(f'✅ Found {len(trans_begin)} transactions')
        print(f'🔍 Begin times: {trans_begin}')
        print(f'🔍 End times: {trans_end}')
        
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
    
    def _detect_transaction_boundaries_streaming(self, audio_clip: AudioFileClip, sr: int, audio_path: str, location_id: str, output_dir: str) -> Tuple[List[float], List[float]]:
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
                    # If we get stdout errors, we can't continue with streaming approach
                    if "'NoneType' object has no attribute 'stdout'" in str(e):
                        print('🔄 Detected stdout error, cannot continue with streaming approach...')
                        audio_clip.close()
                        # Return empty results to trigger fallback in main method
                        return [], []
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
            print(f'🔍 DEBUG: Converting timestamp for filename: {filename}')
            
            # Try to extract timestamp from filename
            # Format: audio_YYYY-MM-DD_HH-MM-SS.mp3
            if '_' in filename:
                parts = filename.split('_')
                print(f'🔍 DEBUG: Filename parts: {parts}')
                if len(parts) >= 3:  # audio_YYYY-MM-DD_HH-MM-SS.mp3
                    date_part = parts[1]  # YYYY-MM-DD
                    time_part = parts[2].split('.')[0]  # HH-MM-SS
                    print(f'🔍 DEBUG: Date part: {date_part}, Time part: {time_part}')
                    try:
                        # Parse date and time
                        date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                        time_parts = time_part.split('-')
                        if len(time_parts) == 3:
                            hour = int(time_parts[0])
                            minute = int(time_parts[1])
                            second = int(time_parts[2])
                            dt = date_obj.replace(hour=hour, minute=minute, second=second)
                            print(f'🔍 DEBUG: Parsed datetime: {dt}')
                        else:
                            dt = date_obj
                            print(f'🔍 DEBUG: Using date only: {dt}')
                    except Exception as e:
                        print(f'🔍 DEBUG: Error parsing datetime: {e}')
                        # Fallback to current time
                        dt = datetime.now()
                        print(f'🔍 DEBUG: Using current time: {dt}')
                else:
                    print(f'🔍 DEBUG: Not enough parts, using current time')
                    # Fallback to current time
                    dt = datetime.now()
            else:
                print(f'🔍 DEBUG: No underscore in filename, using current time')
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
            # Format: audio_YYYY-MM-DD_HH-MM-SS.mp3
            filename = os.path.basename(audio_path)
            if '_' in filename:
                parts = filename.split('_')
                if len(parts) >= 2:  # audio_YYYY-MM-DD_HH-MM-SS.mp3
                    date_part = parts[1]  # YYYY-MM-DD
                    try:
                        dt = datetime.strptime(date_part, "%Y-%m-%d")
                        year = dt.year
                        month = dt.month
                        day = dt.day
                    except:
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
    
    def _fallback_processing(self, audio_path: str, location_id: str, output_dir: str, original_filename: str = None) -> Tuple[List[str], List[float], List[float], List[str], List[str]]:
        """
        Fallback processing using soundfile when AudioFileClip fails
        """
        print('🔄 Using fallback soundfile processing...')
        
        try:
            with sf.SoundFile(audio_path) as f:
                duration = f.frames / f.samplerate
                sr = f.samplerate
                print(f'📊 Audio info: {duration:.1f}s duration, {sr}Hz sample rate')
        except Exception as e:
            print(f'❌ Failed to get audio file info: {e}')
            return [], [], [], [], []
        
        print('🔍 Using simple silence detection...')
        trans_begin, trans_end = self._simple_silence_detection(audio_path, sr, duration)
        
        if not trans_begin:
            print('⚠️ No transactions detected in audio file')
            return [], [], [], [], []
        
        if len(trans_begin) != len(trans_end):
            trans_end.append(duration)
        
        # For timestamp conversion, use original filename if available, otherwise use audio_path
        timestamp_audio_path = original_filename if original_filename else audio_path
        
        trans_reg_begin = [self._convert_timestamp_to_hhmmss(t, timestamp_audio_path) for t in trans_begin]
        trans_reg_end = [self._convert_timestamp_to_hhmmss(t, timestamp_audio_path) for t in trans_end]
        
        audio_clip_paths = []
        for i, (begin_time, end_time) in enumerate(zip(trans_begin, trans_end)):
            try:
                clip_filename = self._generate_clip_filename(location_id, audio_path, trans_reg_begin[i], i)
                clip_path = os.path.join(output_dir, clip_filename)
                
                self._extract_audio_segment_soundfile(audio_path, clip_path, begin_time, end_time, sr)
                
                if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                    audio_clip_paths.append(clip_path)
                    print(f'✅ Created audio clip {i+1}/{len(trans_begin)}: {clip_filename}')
                else:
                    print(f'❌ Failed to create audio clip {i+1}: {clip_filename}')
                    audio_clip_paths.append("")
                    
            except Exception as e:
                print(f'❌ Error creating audio clip {i+1}: {e}')
                audio_clip_paths.append("")
        
        print(f'🎉 Fallback processing completed: {len([p for p in audio_clip_paths if p])} clips created')
        return audio_clip_paths, trans_begin, trans_end, trans_reg_begin, trans_reg_end
    
    def _simple_silence_detection(self, audio_path: str, sr: int, duration: float) -> Tuple[List[float], List[float]]:
        """
        Simple silence detection using soundfile (fallback method)
        """
        trans_begin = []
        trans_end = []
        
        chunk_duration = 300  # 5 minutes
        current_time = 0.0
        prev_state = 0
        
        try:
            with sf.SoundFile(audio_path) as f:
                while current_time < duration:
                    chunk_start_sample = int(current_time * sr)
                    f.seek(chunk_start_sample)
                    
                    remaining_samples = int((duration - current_time) * sr)
                    samples_to_read = min(int(chunk_duration * sr), remaining_samples)
                    
                    if samples_to_read <= 0:
                        break
                    
                    chunk_data = f.read(samples_to_read)
                    
                    chunk_begin, chunk_end, new_state = self._detect_silence_in_chunk(
                        chunk_data, current_time, sr, prev_state
                    )
                    
                    trans_begin.extend(chunk_begin)
                    trans_end.extend(chunk_end)
                    prev_state = new_state
                    
                    current_time += chunk_duration
                    
        except Exception as e:
            print(f'❌ Error in simple silence detection: {e}')
            return [], []
        
        return trans_begin, trans_end
    
    def _detect_silence_in_chunk(self, chunk_data: np.ndarray, chunk_start_time: float, 
                               sr: int, prev_state: int) -> Tuple[List[float], List[float], int]:
        """
        Detect silence in a chunk of audio data
        """
        chunk_begin = []
        chunk_end = []
        
        interval_samples = int(self.SILENCE_INTERVAL * sr)
        
        if len(chunk_data) < interval_samples:
            return chunk_begin, chunk_end, prev_state
        
        index = 0
        current_state = prev_state
        
        while index + interval_samples < len(chunk_data):
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
    
    def _extract_audio_segment_soundfile(self, input_path: str, output_path: str, 
                                       start_time: float, end_time: float, sample_rate: int):
        """
        Extract audio segment using soundfile (fallback method)
        """
        try:
            with sf.SoundFile(input_path) as f:
                f.seek(int(start_time * sample_rate))
                frames_to_read = int((end_time - start_time) * sample_rate)
                seg_data = f.read(frames_to_read)
            
            sf.write(output_path, seg_data, sample_rate)
            
        except Exception as e:
            print(f'❌ Error extracting audio segment with soundfile: {e}')
            raise e