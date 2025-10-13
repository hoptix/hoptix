#!/usr/bin/env python3
"""
Backend Audio Processor - Port of hoptix-flask transcribe_video approach
Uses the proven segmentation strategy that successfully processed 11 parallel 1.2GB AVI files
"""

import os
import logging
import numpy as np
import librosa
import soundfile as sf
from typing import List, Dict, Any
from openai import OpenAI
from config import Settings

logger = logging.getLogger(__name__)

# Initialize settings and client
settings = Settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)
ASR_MODEL = settings.ASR_MODEL

def _segment_active_spans(y: np.ndarray, sr: int, window_s: float = 15.0) -> List[tuple[float, float]]:
    """
    Port of hoptix-flask _segment_active_spans function.
    Uses silence detection to find active audio segments.
    This is the key function that makes large file processing work!
    """
    # Mirrors the simple "average==0 → silence" logic to carve spans
    interval = int(sr * window_s)
    idx, removed, prev_active = 0, 0, 0
    begins, ends = [], []
    y_list = y.tolist()
    
    while idx + interval < len(y_list) and idx >= 0:
        chunk_avg = float(np.average(y_list[idx: idx + interval]))
        if chunk_avg == 0.0:  # Silence detected
            if prev_active == 1:
                ends.append((idx + removed)/sr)
                prev_active = 0
            del y_list[idx: idx+interval]
            removed += interval
        else:  # Active audio
            if prev_active == 0:
                begins.append((idx + removed)/sr)
                prev_active = 1
            idx += interval
    
    if len(begins) != len(ends):
        ends.append((len(y_list)+removed)/sr)
    
    return list(zip(begins, ends))

def transcribe_audio_file(audio_path: str) -> List[Dict]:
    """
    Port of hoptix-flask transcribe_video() function for audio files.
    Uses the proven segmentation approach that worked with 11 parallel 1.2GB AVI files.
    """
    segs: List[Dict] = []
    
    # Create audio directory for segments
    audio_dir = "extracted_audio"
    os.makedirs(audio_dir, exist_ok=True)
    audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
    
    logger.info(f"🎵 Starting audio transcription for: {audio_basename}")
    
    try:
        # Load audio and get duration (memory efficient)
        y, sr = librosa.load(audio_path, sr=None)
        duration = len(y) / sr
        
        logger.info(f"📊 Audio info: {duration:.1f}s duration, {sr}Hz sample rate")
        
        # Segment audio into active spans (this is the magic!)
        spans = _segment_active_spans(y, sr, 15.0) or [(0.0, duration)]
        
        logger.info(f"🎬 Processing {len(spans)} audio segments for {audio_basename}")
        
        # Process each segment individually (not in parallel - this is key!)
        for i, (b, e) in enumerate(spans):
            logger.info(f"🎵 Processing segment {i+1}/{len(spans)}: {b:.1f}s - {e:.1f}s")
            
            # Create segment audio file
            segment_audio = os.path.join(audio_dir, f"{audio_basename}_segment_{i+1:03d}_{int(b)}s-{int(e)}s.wav")
            
            # Extract segment using soundfile (memory efficient)
            with sf.SoundFile(audio_path) as f:
                f.seek(int(b * sr))
                frames_to_read = int((e - b) * sr)
                seg_data = f.read(frames_to_read)
                
            # Write segment to file
            sf.write(segment_audio, seg_data, sr)
            
            # Transcribe the segment
            with open(segment_audio, "rb") as af:
                try:
                    txt = client.audio.transcriptions.create(
                        model=ASR_MODEL,
                        file=af,
                        response_format="text",
                        temperature=0.001,
                        prompt="Label each line as Operator: or Customer: where possible."
                    )
                    text = str(txt).strip()
                    logger.info(f"✅ Segment {i+1} transcribed: {len(text)} characters")
                except Exception as ex:
                    logger.error(f"❌ ASR error for segment {i+1}: {ex}")
                    text = ""
            
            # Clean up segment file immediately (memory management)
            os.remove(segment_audio)
            
            segs.append({"start": float(b), "end": float(e), "text": text})
        
        logger.info(f"🎉 Completed transcription: {len(segs)} segments processed")
        return segs
        
    except Exception as e:
        logger.error(f"❌ Transcription failed: {e}")
        raise

def process_audio_file(audio_path: str, audio_record: Dict) -> List[Dict]:
    """
    Complete audio processing pipeline using hoptix-flask approach.
    This replaces the complex chunking system with the proven segmentation approach.
    """
    logger.info(f"🎵 Starting audio processing pipeline for: {os.path.basename(audio_path)}")
    
    try:
        # Step 1: Transcribe using segmentation approach
        segments = transcribe_audio_file(audio_path)
        
        # Step 2: Process segments into transactions (you'll need to implement this)
        # For now, return segments - you can add transaction splitting later
        logger.info(f"✅ Audio processing completed: {len(segments)} segments")
        return segments
        
    except Exception as e:
        logger.error(f"❌ Audio processing failed: {e}")
        raise
