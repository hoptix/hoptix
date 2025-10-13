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
import soundfile as sf

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
    MAX_WORKERS = 2  # Number of parallel workers

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
    print(f"🔍 DEBUG: audio_path exists: {os.path.exists(audio_path)}")
    print(f"🔍 DEBUG: db provided: {db is not None}")
    print(f"🔍 DEBUG: audio_record provided: {audio_record is not None}")
    
    initial_memory = get_memory_usage()
    print(f"📊 Initial memory usage: {initial_memory:.1f} MB")
    
    # Get total duration without loading audio
    duration = get_duration(audio_path)
    print(f"⏱️  Audio duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"🔍 DEBUG: Duration check - duration > 0: {duration > 0}")
    
    # Check if we need to split the file
    if db and audio_record:
        audio_splitter = AudioSplitter(db, settings)
        should_split, reason = audio_splitter.should_split_audio(audio_path)
        print(f"🔍 File analysis: {reason}")
        print(f"🔍 DEBUG: should_split decision: {should_split}")
        
        if should_split:
            print(f"🔪 Large audio file detected, splitting into chunks...")
            result = transcribe_large_audio_file(audio_path, audio_record, audio_splitter)
            print(f"🔍 DEBUG: transcribe_large_audio_file returned {len(result)} segments")
            return result
    
    # Process as single file (small enough)
    print(f"🎵 Processing as single audio file...")
    result = transcribe_single_audio_file(audio_path)
    print(f"🔍 DEBUG: transcribe_single_audio_file returned {len(result)} segments")
    return result

def transcribe_large_audio_file(audio_path: str, audio_record: Dict, audio_splitter: AudioSplitter) -> List[Dict]:
    """
    Handle large audio files by splitting them into chunks and processing each chunk.
    """
    print(f"🔪 Processing large audio file with chunking...")
    print(f"🔍 DEBUG: audio_record keys: {list(audio_record.keys()) if audio_record else 'None'}")
    print(f"🔍 DEBUG: audio_record id: {audio_record.get('id') if audio_record else 'None'}")
    
    # Split the audio file into chunks
    chunk_records = audio_splitter.process_large_audio_file(audio_path, audio_record)
    print(f"🔍 DEBUG: audio_splitter.process_large_audio_file returned {len(chunk_records)} chunk records")
    
    if not chunk_records:
        print("❌ Failed to split audio file")
        print(f"🔍 DEBUG: chunk_records is empty or None")
        return []
    
    print(f"✅ Successfully split into {len(chunk_records)} chunks")
    for i, chunk in enumerate(chunk_records):
        print(f"🔍 DEBUG: Chunk {i+1}: id={chunk.get('id')}, path={chunk.get('meta', {}).get('local_chunk_path')}")
    
    all_segments = []
    successful_chunks = 0
    failed_chunks = 0
    
    # Process chunks in parallel
    print(f"🚀 Processing {len(chunk_records)} chunks in parallel with {MAX_WORKERS} workers")
    
    def process_chunk_file(chunk_record):
        """Process a single chunk file"""
        chunk_id = chunk_record["id"]
        chunk_path = chunk_record["meta"]["local_chunk_path"]
        chunk_start_time = chunk_record["meta"]["chunk_start_time"]
        
        print(f"🎵 Processing chunk {chunk_id}: {chunk_path}")
        print(f"🔍 DEBUG: chunk_path exists: {os.path.exists(chunk_path)}")
        print(f"🔍 DEBUG: chunk_start_time: {chunk_start_time}")
        print(f"🔍 DEBUG: chunk_record meta: {chunk_record.get('meta', {})}")
        
        try:
            # Transcribe the chunk file
            print(f"🔍 DEBUG: Calling transcribe_single_audio_file for chunk {chunk_id}")
            chunk_segments = transcribe_single_audio_file(chunk_path)
            print(f"🔍 DEBUG: transcribe_single_audio_file returned {len(chunk_segments)} segments for chunk {chunk_id}")
            
            if chunk_segments:
                for i, seg in enumerate(chunk_segments):
                    print(f"🔍 DEBUG: Chunk {chunk_id} segment {i+1}: start={seg.get('start')}, end={seg.get('end')}, text_length={len(seg.get('text', ''))}")
            
            # Adjust timestamps to be relative to original file
            # Account for overlap by adjusting the start time
            overlap_seconds = chunk_record["meta"].get("overlap_seconds", 0)
            adjusted_start_time = chunk_start_time - overlap_seconds
            print(f"🔍 DEBUG: overlap_seconds: {overlap_seconds}, adjusted_start_time: {adjusted_start_time}")
            
            for segment in chunk_segments:
                original_start = segment["start"]
                original_end = segment["end"]
                segment["start"] += adjusted_start_time
                segment["end"] += adjusted_start_time
                print(f"🔍 DEBUG: Adjusted segment timing: {original_start}-{original_end} -> {segment['start']}-{segment['end']}")
            
            print(f"✅ Chunk {chunk_id} completed: {len(chunk_segments)} segments")
            return chunk_segments
            
        except Exception as e:
            print(f"❌ Error processing chunk {chunk_id}: {e}")
            print(f"🔍 DEBUG: Exception type: {type(e).__name__}")
            import traceback
            print(f"🔍 DEBUG: Full traceback:")
            traceback.print_exc()
            return []
    
    # Process chunks in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all chunk processing tasks
        print(f"🔍 DEBUG: Submitting {len(chunk_records)} chunk processing tasks")
        future_to_chunk = {
            executor.submit(process_chunk_file, chunk_record): chunk_record
            for chunk_record in chunk_records
        }
        print(f"🔍 DEBUG: All {len(future_to_chunk)} tasks submitted to executor")
        
        # Collect results as they complete
        completed_count = 0
        for future in as_completed(future_to_chunk):
            chunk_record = future_to_chunk[future]
            completed_count += 1
            chunk_id = chunk_record["id"]
            print(f"🔍 DEBUG: Processing result {completed_count}/{len(chunk_records)} for chunk {chunk_id}")
            
            try:
                chunk_segments = future.result()
                print(f"🔍 DEBUG: Chunk {chunk_id} result: {len(chunk_segments)} segments")
                
                if chunk_segments:
                    all_segments.extend(chunk_segments)
                    successful_chunks += 1
                    print(f"🔍 DEBUG: Added {len(chunk_segments)} segments from chunk {chunk_id}. Total segments: {len(all_segments)}")
                else:
                    failed_chunks += 1
                    print(f"🔍 DEBUG: Chunk {chunk_id} returned 0 segments - marked as failed")
                
                # Periodic memory cleanup
                if len(all_segments) % CLEANUP_FREQUENCY == 0:
                    gc.collect()
                    if MEMORY_MONITORING:
                        current_memory = get_memory_usage()
                        print(f"📊 Memory usage after cleanup: {current_memory:.1f} MB")
                    print(f"🔍 DEBUG: Performed garbage collection at {len(all_segments)} segments")
                    
            except Exception as e:
                failed_chunks += 1
                print(f"❌ Chunk processing failed for chunk {chunk_id}: {e}")
                print(f"🔍 DEBUG: Exception type: {type(e).__name__}")
                import traceback
                print(f"🔍 DEBUG: Full traceback:")
                traceback.print_exc()
                continue
    
    # Clean up chunk files
    print(f"🔍 DEBUG: Cleaning up {len(chunk_records)} chunk files")
    audio_splitter.cleanup_chunk_files(chunk_records)
    
    final_memory = get_memory_usage()
    print(f"\n🎉 Completed chunked transcription!")
    print(f"📊 Final memory usage: {final_memory:.1f} MB")
    print(f"📝 Total segments transcribed: {len(all_segments)}")
    print(f"🔍 DEBUG: Chunk processing summary:")
    print(f"🔍 DEBUG: - Successful chunks: {successful_chunks}")
    print(f"🔍 DEBUG: - Failed chunks: {failed_chunks}")
    print(f"🔍 DEBUG: - Total chunks processed: {successful_chunks + failed_chunks}")
    print(f"🔍 DEBUG: - Success rate: {(successful_chunks / (successful_chunks + failed_chunks) * 100):.1f}%" if (successful_chunks + failed_chunks) > 0 else "N/A")
    
    return all_segments

def transcribe_single_audio_file(audio_path: str) -> List[Dict]:
    """
    Transcribe a single audio file using soundfile-based approach for better reliability.
    """
    print(f"🎵 Transcribing single audio file: {os.path.basename(audio_path)}")
    print(f"🔍 DEBUG: audio_path exists: {os.path.exists(audio_path)}")
    print(f"🔍 DEBUG: audio_path size: {os.path.getsize(audio_path) if os.path.exists(audio_path) else 'N/A'} bytes")
    
    # Get file info using soundfile (more memory efficient)
    try:
        with sf.SoundFile(audio_path) as f:
            sr = f.samplerate
            frames = f.frames
            duration = frames / float(sr)
            channels = f.channels
            
        print(f"📊 Audio Info: {duration:.1f}s, {sr}Hz, {channels} channels, {frames:,} frames")
        print(f"🔍 DEBUG: duration > 0: {duration > 0}")
    except Exception as e:
        print(f"❌ Failed to read audio file info: {e}")
        return []
    
    # For large files, use segmentation approach to avoid memory issues
    max_seg_s = 600.0  # 10 minutes max per segment (reduced from 20 minutes)
    
    # Create segments based on duration rather than loading entire file
    if duration <= max_seg_s:
        # File is small enough to process as one segment
        final_spans = [(0.0, duration)]
        print(f"📏 File is small enough ({duration:.1f}s), processing as single segment")
    else:
        # Split into 20-minute chunks with small overlap
        overlap_s = 5.0  # 5 second overlap
        final_spans = []
        current_start = 0.0
        
        while current_start < duration:
            current_end = min(current_start + max_seg_s, duration)
            final_spans.append((current_start, current_end))
            current_start = current_end - overlap_s
            
        print(f"📏 File split into {len(final_spans)} segments of ~{max_seg_s/60:.1f}min each")

    # Transcribe each segment using memory-efficient approach
    print(f"🧩 Processing {len(final_spans)} audio segments for ASR")
    audio_dir = "extracted_audio"
    os.makedirs(audio_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(audio_path))[0]

    segments = []
    for i, (b, e) in enumerate(final_spans, start=1):
        print(f"🎵 Processing segment {i}/{len(final_spans)}: {b:.1f}s - {e:.1f}s")
        
        # Monitor memory usage
        if MEMORY_MONITORING:
            current_memory = get_memory_usage()
            print(f"📊 Memory usage before segment {i}: {current_memory:.1f} MB")
        
        # Extract segment using soundfile (memory efficient)
        seg_path = os.path.join(audio_dir, f"{base}_seg_{i:03d}_{int(b)}s-{int(e)}s.wav")
        
        try:
            # Use soundfile to extract just this segment
            with sf.SoundFile(audio_path) as f:
                # Seek to start position
                f.seek(int(b * sr))
                # Read only the frames we need
                frames_to_read = int((e - b) * sr)
                seg_data = f.read(frames_to_read)
                
            # Write segment to file
            sf.write(seg_path, seg_data, sr)
            
            # Transcribe the segment
            with open(seg_path, "rb") as af:
                print(f"🔍 DEBUG: Calling OpenAI ASR with model: {ASR_MODEL}")
                txt = client.audio.transcriptions.create(
                    model=ASR_MODEL,
                    file=af,
                    response_format="text",
                    temperature=0.001,
                    prompt="Label each line as Operator: or Customer: where possible."
                )
            text = str(txt).strip()
            print(f"✅ ASR {i}/{len(final_spans)}: {len(text)} chars")
            print(f"🔍 DEBUG: First 200 chars of transcription: {text[:200]}...")
            
            # Clean up segment file immediately to save disk space
            os.remove(seg_path)
            
            # Force garbage collection after each segment to free memory
            if i % CLEANUP_FREQUENCY == 0:
                gc.collect()
                if MEMORY_MONITORING:
                    memory_after = get_memory_usage()
                    print(f"📊 Memory usage after cleanup: {memory_after:.1f} MB")
            
        except Exception as asr_err:
            print(f"❌ ASR failed for segment {i}: {asr_err}")
            print(f"🔍 DEBUG: ASR exception type: {type(asr_err).__name__}")
            import traceback
            print(f"🔍 DEBUG: ASR full traceback:")
            traceback.print_exc()
            text = ""
            # Clean up failed segment file
            if os.path.exists(seg_path):
                os.remove(seg_path)
                
        segments.append({"start": float(b), "end": float(e), "text": text})

    print(f"✅ Transcription completed: {len(segments)} segments generated")
    return segments

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
