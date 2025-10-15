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
            original_filename: The original filename of the audio, used for timestamp parsing.
            
        Returns:
            Tuple of (audio_clip_paths, begin_times, end_times, reg_begin_times, reg_end_times)
        """
        print(f'🎵 Processing audio file: {audio_path}')
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        print('Loading Audio Info (Memory Safe)')
        # Get audio info without loading entire file
        with sf.SoundFile(audio_path) as f:
            sr = f.samplerate
            total_frames = f.frames
            duration = total_frames / sr
        
        print('Splicing Audio and Generating Relative Beginning and Ending Timestamps (Chunked)')
        trans_begin = []
        trans_end = []
        interval = self.AUDIO_SAMPLE_RATE * self.SILENCE_INTERVAL
        current_time = 0.0
        prev_state = 0  # 0 = silence, 1 = active
        
        # Process in chunks to avoid memory issues
        chunk_duration = 300  # 5 minutes at a time
        print(f'Processing {duration:.1f}s audio in {chunk_duration}s chunks...')
        
        with sf.SoundFile(audio_path) as f:
            while current_time < duration:
                # Calculate chunk boundaries
                chunk_start_frame = int(current_time * sr)
                chunk_end_frame = min(int((current_time + chunk_duration) * sr), total_frames)
                frames_to_read = chunk_end_frame - chunk_start_frame
                
                if frames_to_read <= 0:
                    break
                
                # Read chunk
                f.seek(chunk_start_frame)
                chunk_data = f.read(frames_to_read)
                
                # Process chunk for silence detection
                chunk_begin, chunk_end, new_state = self._detect_silence_in_chunk(
                    chunk_data, current_time, sr, prev_state
                )
                
                # Update transaction boundaries
                trans_begin.extend(chunk_begin)
                trans_end.extend(chunk_end)
                
                # Update state for next chunk
                prev_state = new_state
                
                current_time += chunk_duration

        print(f"Found {len(trans_begin)} transactions")
        print(f"Begin times: {trans_begin}")
        print(f"End times: {trans_end}")

        if len(trans_begin) != len(trans_end):
            trans_end.append(duration)

        # Generate regularized timestamps
        print('Regularizing Beginning and Ending Timestamps')
        # For timestamp conversion, use original filename if available, otherwise use audio_path
        timestamp_audio_path = original_filename if original_filename else audio_path
        trans_reg_begin = [self._convert_timestamp_to_hhmmss(i, timestamp_audio_path) for i in trans_begin]
        trans_reg_end = [self._convert_timestamp_to_hhmmss(i, timestamp_audio_path) for i in trans_end]

        # Create audio clips
        print('Creating audio clips...')
        audio_clip_paths = []
        
        for i in range(len(trans_begin)):
            try:
                # Generate unique filename
                clip_filename = self._generate_clip_filename(
                    location_id, timestamp_audio_path, trans_reg_begin[i], i
                )
                clip_path = os.path.join(output_dir, clip_filename)
                
                # Extract audio segment using soundfile
                self._extract_audio_segment_soundfile(audio_path, clip_path, trans_begin[i], trans_end[i], sr)
                
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
        
        print(f'🎉 Audio processing completed: {len([p for p in audio_clip_paths if p])} clips created')
        return audio_clip_paths, trans_begin, trans_end, trans_reg_begin, trans_reg_end
    
    def _convert_timestamp_to_hhmmss(self, seconds: float, audio_path: str) -> str:
        """
        Convert seconds to HH:MM:SS format based on audio file timestamp
        Adapted from convert_timestamp function
        """
        try:
            # Extract timestamp from filename (assuming format like original)
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
    
    def _detect_silence_in_chunk(self, chunk_data: np.ndarray, chunk_start_time: float, 
                               sr: int, prev_state: int) -> Tuple[List[float], List[float], int]:
        """
        Detect silence in a chunk of audio data (memory safe)
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
        Extract audio segment using soundfile
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