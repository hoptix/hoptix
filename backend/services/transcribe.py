from services.converter import get_duration
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
        subprocess.run(cmd, check=True, capture_output=True, stderr=subprocess.DEVNULL)
        
        # Use ffmpeg to detect silence
        silence_cmd = [
            "ffmpeg", "-i", chunk_path,
            "-af", f"silencedetect=noise={SILENCE_THRESHOLD}dB:d=1.0",
            "-f", "null", "-"
        ]
        
        result = subprocess.run(silence_cmd, capture_output=True, text=True, stderr=subprocess.DEVNULL)
        
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

def process_audio_chunk(audio_path: str, chunk_start: float, chunk_duration: float, 
                       global_offset: float, chunk_index: int, total_chunks: int) -> List[Dict]:
    """
    Process a single chunk of audio for transcription.
    Returns list of transcript segments with global timestamps.
    """
    print(f"🎵 Processing chunk {chunk_index + 1}/{total_chunks} ({chunk_start:.1f}s - {chunk_start + chunk_duration:.1f}s)")
    
    # Detect active segments in this chunk
    active_segments = detect_silence_ffmpeg(audio_path, chunk_start, chunk_duration)
    
    if not active_segments:
        print(f"   ⏸️  No active segments found in chunk {chunk_index + 1}")
        return []
    
    print(f"   🎬 Found {len(active_segments)} active segments in chunk {chunk_index + 1}")
    
    chunk_segments = []
    
    for i, (seg_start, seg_end) in enumerate(active_segments):
        # Convert to global timestamps
        global_start = global_offset + seg_start
        global_end = global_offset + seg_end
        
        # Create temporary file for this segment
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            segment_path = tmp_file.name
        
        try:
            # Extract segment using ffmpeg
            clip_audio_with_ffmpeg(audio_path, segment_path, global_start, global_end)
            
            # Transcribe the segment
            with open(segment_path, "rb") as af:
                try:
                    txt = client.audio.transcriptions.create(
                        model=ASR_MODEL,
                        file=af,
                        response_format="text",
                        temperature=0.001,
                        prompt="Label each line as Operator: or Customer: where possible."
                    )
                    text = str(txt).strip()
                    print(f"   ✅ Segment {i+1} transcribed: {len(text)} characters")
                except Exception as ex:
                    print(f"   ❌ ASR error for segment {i+1}: {ex}")
                    text = ""
            
            if text:  # Only add segments with actual text
                chunk_segments.append({
                    "start": global_start,
                    "end": global_end,
                    "text": text
                })
                
        finally:
            # Clean up temporary segment file
            if os.path.exists(segment_path):
                os.remove(segment_path)
    
    # Update progress tracking
    global completed_chunks
    with progress_lock:
        completed_chunks += 1
        print(f"✅ Completed chunk {chunk_index + 1}/{total_chunks} ({completed_chunks}/{total_chunks} total)")
    
    return chunk_segments

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
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ss", str(start_time),  # start time
        "-t", str(end_time - start_time),  # duration
        "-vn",  # no video
        "-acodec", "pcm_s16le",  # WAV PCM 16-bit
        "-ar", "16000",  # 16 kHz sample rate
        "-ac", "1",  # mono
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True, stderr=subprocess.DEVNULL)
    return output_path

# ---------- 1) TRANSCRIBE (chunked processing for memory efficiency) ----------
def transcribe_audio(audio_path: str) -> List[Dict]:
    """
    Transcribe audio using chunked processing to avoid memory issues.
    Processes audio in fixed-size chunks without loading entire file into memory.
    """
    print(f"🎬 Starting chunked transcription for {audio_path}")
    initial_memory = get_memory_usage()
    print(f"📊 Initial memory usage: {initial_memory:.1f} MB")
    
    # Get total duration without loading audio
    duration = get_duration(audio_path)
    print(f"⏱️  Audio duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    # Calculate number of chunks needed
    total_chunks = int((duration + CHUNK_SIZE_SECONDS - 1) // CHUNK_SIZE_SECONDS)
    print(f"📦 Processing in {total_chunks} chunks of {CHUNK_SIZE_SECONDS} seconds each")
    
    all_segments = []
    
    # Process chunks with small overlap to handle boundary transactions
    CHUNK_OVERLAP = 30  # 30 seconds overlap between chunks
    
    # Reset progress tracking
    global completed_chunks
    completed_chunks = 0
    
    if PARALLEL_CHUNKS:
        print(f"🚀 Processing {total_chunks} chunks in parallel with {MAX_WORKERS} workers")
        
        # Create list of chunk tasks
        chunk_tasks = []
        for chunk_index in range(total_chunks):
            chunk_start = max(0, chunk_index * CHUNK_SIZE_SECONDS - CHUNK_OVERLAP)
            chunk_duration = min(CHUNK_SIZE_SECONDS + CHUNK_OVERLAP, duration - chunk_start)
            chunk_tasks.append((chunk_index, chunk_start, chunk_duration))
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_chunk = {
                executor.submit(
                    process_audio_chunk,
                    audio_path,
                    chunk_start,
                    chunk_duration,
                    chunk_start,  # global_offset
                    chunk_index,
                    total_chunks
                ): chunk_index for chunk_index, chunk_start, chunk_duration in chunk_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk_index = future_to_chunk[future]
                try:
                    chunk_segments = future.result()
                    all_segments.extend(chunk_segments)
                    
                    # Periodic memory cleanup
                    if completed_chunks % CLEANUP_FREQUENCY == 0:
                        gc.collect()
                        
                except Exception as e:
                    print(f"   ❌ Error processing chunk {chunk_index + 1}: {e}")
                    continue
    else:
        print(f"🔄 Processing {total_chunks} chunks sequentially")
        
        # Sequential processing (original approach)
        for chunk_index in range(total_chunks):
            chunk_start = max(0, chunk_index * CHUNK_SIZE_SECONDS - CHUNK_OVERLAP)
            chunk_duration = min(CHUNK_SIZE_SECONDS + CHUNK_OVERLAP, duration - chunk_start)
            
            print(f"\n🔄 Processing chunk {chunk_index + 1}/{total_chunks}")
            
            chunk_memory_before = get_memory_usage() if MEMORY_MONITORING else 0
            
            try:
                # Process this chunk
                chunk_segments = process_audio_chunk(
                    audio_path, 
                    chunk_start, 
                    chunk_duration, 
                    chunk_start,  # global_offset
                    chunk_index, 
                    total_chunks
                )
                
                all_segments.extend(chunk_segments)
                
                if MEMORY_MONITORING:
                    chunk_memory_after = get_memory_usage()
                    print(f"   📊 Memory: {chunk_memory_before:.1f} → {chunk_memory_after:.1f} MB")
                    
                    # Force cleanup if memory usage is too high
                    if chunk_memory_after > MAX_MEMORY_MB:
                        print(f"   🧹 High memory usage detected, forcing cleanup...")
                        gc.collect()
                
                # Periodic cleanup
                if (chunk_index + 1) % CLEANUP_FREQUENCY == 0:
                    gc.collect()
                
            except Exception as e:
                print(f"   ❌ Error processing chunk {chunk_index + 1}: {e}")
                # Continue with next chunk instead of failing completely
                continue
    
    final_memory = get_memory_usage()
    print(f"\n🎉 Completed chunked transcription!")
    print(f"📊 Final memory usage: {final_memory:.1f} MB (started with {initial_memory:.1f} MB)")
    print(f"📝 Total segments transcribed: {len(all_segments)}")
    
    # Validate timing accuracy
    if all_segments:
        validate_timing_accuracy(all_segments, duration)
    
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
