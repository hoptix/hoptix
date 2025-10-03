from services.converter import get_duration
import os
import numpy as np
from typing import List, Dict
import librosa
import subprocess
from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# parses transactions from audio files and feeds them to the grader@contextlib.contextmanager
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
        "-acodec", "pcm_s16le",  # WAV format
        output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path

# ---------- 1) TRANSCRIBE (extract spans, per‑span ASR) ----------
def transcribe_audio(audio_path: str) -> List[Dict]:
    segs: List[Dict] = []
    
    # Create audio directory for segments
    audio_dir = "extracted_audio"

    duration = get_duration(audio_path)
    
    y, sr = librosa.load(audio_path, sr=None)
    spans = segment_active_spans(y, sr, 15.0) or [(0.0, duration)]
        
    print(f"🎬 Processing {len(spans)} audio segments for {audio_path}")
        
    for i, (b, e) in enumerate(spans):
        # Create permanent segment audio file instead of temporary
        segment_audio = os.path.join(audio_dir, f"{audio_path}_segment_{i+1:03d}_{int(b)}s-{int(e)}s.mp3")
        
        # Ensure end time doesn't exceed video duration
        end_time = min(int(e+1), duration)
        segment_audio = clip_audio_with_ffmpeg(audio_path, segment_audio, int(b), end_time)
        
        print(f"🎵 Saving segment {i+1}/{len(spans)}: {segment_audio}")

        with open(segment_audio, "rb") as af:
            try:
                txt = client.audio.transcriptions.create(
                    model=client.ASR_MODEL,
                    file=af,
                    response_format="text",
                    temperature=0.001,
                    prompt="Label each line as Operator: or Customer: where possible."
                )
                text = str(txt)
                print(f"✅ Segment {i+1} transcribed: {len(text)} characters")
            except Exception as ex:
                print(f"❌ ASR error for segment {i+1}: {ex}")
                text = ""
        
            # Don't delete the segment audio file - keep it saved
    print(f"💾 Segment audio preserved: {segment_audio}")

    segs.append({"start": float(b), "end": float(e), "text": text})
    
    print(f"🎉 Completed transcription: {len(segs)} segments saved")
    return segs
