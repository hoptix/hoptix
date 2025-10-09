from services.converter import get_duration
from services.wav_splitter import AudioSplitter
import os
import numpy as np
from typing import List, Dict, Tuple
import librosa
import subprocess
from openai import OpenAI
from config import Settings
import tempfile
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

settings = Settings()

client = OpenAI(api_key=settings.OPENAI_API_KEY)
ASR_MODEL = settings.ASR_MODEL

# Import chunked processing configuration
try:
    from config.chunked_processing import (
        CHUNK_SIZE_SECONDS, SILENCE_THRESHOLD, MIN_ACTIVE_DURATION,
        MAX_MEMORY_MB, CLEANUP_FREQUENCY, VERBOSE_LOGGING, MEMORY_MONITORING,
        PARALLEL_CHUNKS, MAX_WORKERS
    )
except ImportError:
    # Fallback configuration if config file doesn't exist
    CHUNK_SIZE_SECONDS = 600  # 10 minutes per chunk
    SILENCE_THRESHOLD = -40  # dB threshold for silence detection
    MIN_ACTIVE_DURATION = 5.0  # Minimum duration for active segments
    MAX_MEMORY_MB = 1000  # Maximum memory usage before forcing cleanup
    CLEANUP_FREQUENCY = 5  # Force garbage collection every N chunks
    VERBOSE_LOGGING = True
    MEMORY_MONITORING = True
    PARALLEL_CHUNKS = True  # Enable parallel processing
    MAX_WORKERS = 10  # Number of parallel workers

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

# Thread-safe progress tracking
progress_lock = threading.Lock()
completed_chunks = 0

def detect_silence_ffmpeg(audio_path: str, start_time: float, duration: float) -> List[Tuple[float, float]]:
    """
    Use ffmpeg to detect silence in a chunk without loading full audio into memory.
    Returns list of (start, end) tuples for active (non-silent) segments.
    """
    # Create temporary file for this chunk
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        chunk_path = tmp_file.name
    
    try:
        # Extract chunk using ffmpeg with precise timing
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),  # Seek before input for better precision
            "-i", audio_path,
            "-t", str(duration),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-avoid_negative_ts", "make_zero",  # Handle timing edge cases
            chunk_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Use ffmpeg to detect silence
        silence_cmd = [
            "ffmpeg", "-i", chunk_path,
            "-af", f"silencedetect=noise={SILENCE_THRESHOLD}dB:d=1.0",
            "-f", "null", "-"
        ]
        
        result = subprocess.run(silence_cmd, capture_output=True, text=True)
        
        # Parse silence detection output
        active_segments = []
        silence_starts = []
        silence_ends = []
        
        for line in result.stderr.split('\n'):
            if 'silence_start' in line:
                # Extract silence start time
                start_match = line.split('silence_start: ')[1].split()[0]
                silence_starts.append(float(start_match))
            elif 'silence_end' in line:
                # Extract silence end time
                end_match = line.split('silence_end: ')[1].split()[0]
                silence_ends.append(float(end_match))
        
        # Convert silence periods to active periods
        current_time = 0.0
        for i, silence_start in enumerate(silence_starts):
            # Add active segment before silence
            if silence_start > current_time + MIN_ACTIVE_DURATION:
                active_segments.append((current_time, silence_start))
            current_time = silence_ends[i] if i < len(silence_ends) else duration
        
        # Add final active segment if there's remaining time
        if current_time < duration - MIN_ACTIVE_DURATION:
            active_segments.append((current_time, duration))
            
        return active_segments
        
    finally:
        # Clean up temporary chunk file
        if os.path.exists(chunk_path):
            os.remove(chunk_path)


# Legacy function - kept for backward compatibility but not used in new approach
def segment_active_spans(y: np.ndarray, sr: int, window_s: float = 15.0) -> List[tuple[float,float]]:
    # Mirrors your simple "average==0 → silence" logic to carve spans.
    interval = int(sr * window_s)
    idx, removed, prev_active = 0, 0, 0
    begins, ends = [], []
    y_list = y.tolist()
    while idx + interval < len(y_list) and idx >= 0:
        chunk_avg = float(np.average(y_list[idx: idx + interval]))
        if chunk_avg == 0.0:
            if prev_active == 1:
                ends.append((idx + removed)/sr)
                prev_active = 0
            del y_list[idx: idx+interval]
            removed += interval
        else:
            if prev_active == 0:
                begins.append((idx + removed)/sr)
                prev_active = 1
            idx += interval
    if len(begins) != len(ends):
        ends.append((len(y_list)+removed)/sr)
    return list(zip(begins, ends))

def clip_audio_with_ffmpeg(input_path: str, output_path: str, start_time: float, end_time: float):
    """Extract audio segment using ffmpeg (works for WAV, MP3, and other formats)"""
    duration = end_time - start_time
    cmd = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-ss", str(start_time),  # start time
        "-i", input_path,
        "-t", str(duration),  # duration
        "-vn",  # no video
        "-acodec", "pcm_s16le",  # WAV PCM 16-bit
        "-ar", "16000",  # 16 kHz sample rate
        "-ac", "1",  # mono
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path

# ---------- 1) TRANSCRIBE (using proper file chunking) ----------
def transcribe_audio(audio_path: str, db=None, audio_record=None) -> List[Dict]:
    """
    Transcribe audio using proper file chunking approach.
    If the file is large, it will be split into physical chunks and processed independently.
    """
    print(f"🎬 Starting transcription for {audio_path}")
    initial_memory = get_memory_usage()
    print(f"📊 Initial memory usage: {initial_memory:.1f} MB")
    
    # Get total duration without loading audio
    duration = get_duration(audio_path)
    print(f"⏱️  Audio duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    # Check if we need to split the file
    if db and audio_record:
        audio_splitter = AudioSplitter(db, settings)
        should_split, reason = audio_splitter.should_split_audio(audio_path)
        print(f"🔍 File analysis: {reason}")
        
        if should_split:
            print(f"🔪 Large audio file detected, splitting into chunks...")
            return transcribe_large_audio_file(audio_path, audio_record, audio_splitter)
    
    # Process as single file (small enough)
    print(f"🎵 Processing as single audio file...")
    return transcribe_single_audio_file(audio_path)

def transcribe_large_audio_file(audio_path: str, audio_record: Dict, audio_splitter: AudioSplitter) -> List[Dict]:
    """
    Handle large audio files by splitting them into chunks and processing each chunk.
    """
    print(f"🔪 Processing large audio file with chunking...")
    
    # Split the audio file into chunks
    chunk_records = audio_splitter.process_large_audio_file(audio_path, audio_record)
    
    if not chunk_records:
        print("❌ Failed to split audio file")
        return []
    
    print(f"✅ Successfully split into {len(chunk_records)} chunks")
    
    all_segments = []
    
    # Process chunks in parallel
    print(f"🚀 Processing {len(chunk_records)} chunks in parallel with {MAX_WORKERS} workers")
    
    def process_chunk_file(chunk_record):
        """Process a single chunk file"""
        chunk_id = chunk_record["id"]
        chunk_path = chunk_record["meta"]["local_chunk_path"]
        chunk_start_time = chunk_record["meta"]["chunk_start_time"]
        
        print(f"🎵 Processing chunk {chunk_id}: {chunk_path}")
        
        try:
            # Transcribe the chunk file
            chunk_segments = transcribe_single_audio_file(chunk_path)
            
            # Adjust timestamps to be relative to original file
            for segment in chunk_segments:
                segment["start"] += chunk_start_time
                segment["end"] += chunk_start_time
            
            print(f"✅ Chunk {chunk_id} completed: {len(chunk_segments)} segments")
            return chunk_segments
            
        except Exception as e:
            print(f"❌ Error processing chunk {chunk_id}: {e}")
            return []
    
    # Process chunks in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all chunk processing tasks
        future_to_chunk = {
            executor.submit(process_chunk_file, chunk_record): chunk_record
            for chunk_record in chunk_records
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_chunk):
            chunk_record = future_to_chunk[future]
            try:
                chunk_segments = future.result()
                all_segments.extend(chunk_segments)
                
                # Periodic memory cleanup
                if len(all_segments) % CLEANUP_FREQUENCY == 0:
                    gc.collect()
                    
            except Exception as e:
                print(f"❌ Chunk processing failed: {e}")
                continue
    
    # Clean up chunk files
    audio_splitter.cleanup_chunk_files(chunk_records)
    
    final_memory = get_memory_usage()
    print(f"\n🎉 Completed chunked transcription!")
    print(f"📊 Final memory usage: {final_memory:.1f} MB")
    print(f"📝 Total segments transcribed: {len(all_segments)}")
    
    return all_segments

def transcribe_single_audio_file(audio_path: str) -> List[Dict]:
    """
    Transcribe a single audio file by dividing it into equal chunks and processing in parallel.
    Each chunk is processed by a different worker with preserved timestamps.
    """
    print(f"🎵 Transcribing single audio file: {os.path.basename(audio_path)}")
    
    # Get duration
    duration = get_duration(audio_path)
    print(f"   ⏱️  Audio duration: {duration:.1f} seconds")
    
    # For short files, divide into 6 equal parts for parallel processing
    num_chunks = 6
    chunk_duration = duration / num_chunks
    
    print(f"   🔪 Dividing into {num_chunks} equal chunks of {chunk_duration:.1f}s each")
    
    def process_audio_chunk(chunk_index: int, chunk_start: float, chunk_duration: float) -> List[Dict]:
        """Process a single audio chunk"""
        chunk_end = min(chunk_start + chunk_duration, duration)
        actual_chunk_duration = chunk_end - chunk_start
        
        print(f"   🎯 Processing chunk {chunk_index + 1}/{num_chunks}: {chunk_start:.1f}s - {chunk_end:.1f}s")
        
        # Create temporary file for this chunk
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            chunk_path = tmp_file.name
        
        try:
            # Extract chunk using ffmpeg
            clip_audio_with_ffmpeg(audio_path, chunk_path, chunk_start, chunk_end)
            
            # Transcribe the entire chunk
            with open(chunk_path, "rb") as af:
                try:
                    txt = client.audio.transcriptions.create(
                        model=ASR_MODEL,
                        file=af,
                        response_format="text",
                        temperature=0.001,
                        prompt="Label each line as Operator: or Customer: where possible."
                    )
                    text = str(txt).strip()
                    print(f"   ✅ Chunk {chunk_index + 1} transcribed: {len(text)} characters")
                except Exception as ex:
                    print(f"   ❌ ASR error for chunk {chunk_index + 1}: {ex}")
                    text = ""
            
            if text:  # Only add chunks with actual text
                return [{
                    "start": chunk_start,
                    "end": chunk_end,
                    "text": text
                }]
            else:
                return []
                
        finally:
            # Clean up temporary chunk file
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
    
    # Process chunks in parallel
    print(f"   🚀 Processing {num_chunks} chunks in parallel with {MAX_WORKERS} workers")
    
    all_segments = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all chunk processing tasks
        future_to_chunk = {
            executor.submit(process_audio_chunk, i, i * chunk_duration, chunk_duration): i
            for i in range(num_chunks)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_chunk):
            chunk_index = future_to_chunk[future]
            try:
                chunk_segments = future.result()
                all_segments.extend(chunk_segments)
            except Exception as e:
                print(f"   ❌ Error processing chunk {chunk_index + 1}: {e}")
                continue
    
    # Sort segments by start time to maintain chronological order
    all_segments.sort(key=lambda x: x['start'])
    
    print(f"✅ Single file transcription completed: {len(all_segments)} chunks")
    return all_segments

def validate_timing_accuracy(segments: List[Dict], total_duration: float):
    """Validate that segment timings are accurate and don't exceed file duration"""
    print(f"\n🔍 Timing Validation:")
    
    timing_issues = []
    for i, segment in enumerate(segments):
        start = segment['start']
        end = segment['end']
        
        # Check for timing issues
        if start < 0:
            timing_issues.append(f"Segment {i+1}: Negative start time ({start:.2f}s)")
        if end > total_duration:
            timing_issues.append(f"Segment {i+1}: End time exceeds duration ({end:.2f}s > {total_duration:.2f}s)")
        if start >= end:
            timing_issues.append(f"Segment {i+1}: Start >= End ({start:.2f}s >= {end:.2f}s)")
        if end - start < 0.1:
            timing_issues.append(f"Segment {i+1}: Very short duration ({end-start:.2f}s)")
    
    if timing_issues:
        print(f"   ⚠️  Found {len(timing_issues)} timing issues:")
        for issue in timing_issues[:5]:  # Show first 5 issues
            print(f"      - {issue}")
        if len(timing_issues) > 5:
            print(f"      - ... and {len(timing_issues) - 5} more")
    else:
        print(f"   ✅ All {len(segments)} segments have valid timing")
    
    # Show timing coverage
    total_segment_duration = sum(seg['end'] - seg['start'] for seg in segments)
    coverage = (total_segment_duration / total_duration * 100) if total_duration > 0 else 0
    print(f"   📊 Audio coverage: {coverage:.1f}% of total duration")
