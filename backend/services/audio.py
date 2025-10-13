import os
import numpy as np
import librosa
import soundfile as sf
from datetime import datetime
from typing import List, Tuple

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
        
        # Load audio file
        print('📊 Loading audio file...')
        try:
            y, sr = librosa.load(audio_path, sr=None)
            duration = len(y) / float(sr)
            print(f'📊 Audio loaded: {duration:.1f}s duration, {sr}Hz sample rate')
        except Exception as e:
            print(f'❌ Failed to load audio file: {e}')
            return [], [], [], [], []
        
        # Detect transaction boundaries using silence detection
        print('🔍 Detecting transaction boundaries using silence detection...')
        trans_begin, trans_end = self._detect_transaction_boundaries(y, sr)
        
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
                
                # Extract audio segment
                self._extract_audio_segment(audio_path, clip_path, begin_time, end_time, sr)
                
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
    
    def _detect_transaction_boundaries(self, y: np.ndarray, sr: int) -> Tuple[List[float], List[float]]:
        """
        Detect transaction boundaries using silence detection
        Adapted from the original silence detection logic
        """
        trans_begin = []
        trans_end = []
        
        # Convert to list for processing (like original code)
        y_copy = y.tolist().copy()
        removed = 0
        interval = sr * self.SILENCE_INTERVAL
        index = 0
        prev = 0
        
        print(f'🔍 Processing audio with {self.SILENCE_INTERVAL}s silence intervals')
        
        while index + interval < len(y_copy):
            # Check if this interval is silent (average amplitude near zero)
            chunk_avg = float(np.average(y_copy[index : index + interval]))
            
            if chunk_avg == 0.0:  # Silent period detected
                if prev == 1:  # We were in an active period, now entering silence
                    trans_end.append((index + removed) / sr)
                    prev = 0
                # Remove silent period
                del y_copy[index : index + interval]
                removed += interval
            else:  # Active period detected
                if prev == 0:  # We were in silence, now entering active period
                    trans_begin.append((index + removed) / sr)
                    prev = 1
                index += interval
        
        # Handle case where audio ends during active period
        if len(trans_begin) != len(trans_end):
            # Add final end time
            final_time = (len(y_copy) + removed) / sr
            trans_end.append(final_time)
        
        return trans_begin, trans_end
    
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
    
    def _extract_audio_segment(self, input_path: str, output_path: str, 
                             start_time: float, end_time: float, sample_rate: int):
        """
        Extract audio segment using soundfile (memory efficient)
        """
        try:
            # Use soundfile to extract just this segment
            with sf.SoundFile(input_path) as f:
                # Seek to start position
                f.seek(int(start_time * sample_rate))
                # Read only the frames we need
                frames_to_read = int((end_time - start_time) * sample_rate)
                seg_data = f.read(frames_to_read)
            
            # Write segment to file
            sf.write(output_path, seg_data, sample_rate)
            
        except Exception as e:
            print(f'❌ Error extracting audio segment: {e}')
            raise e