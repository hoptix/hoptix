import os
import soundfile as sf
from typing import Dict, Any
from openai import OpenAI
from config import Settings

ASR_MODEL = Settings.ASR_MODEL

client = OpenAI()

def transcribe_audio_clip(audio_clip_path: str, begin_time: float, end_time: float,
                         index: int) -> Dict[str, Any]:
        """
        Transcribe a single audio clip (from audio.py processing)

        Args:
            audio_clip_path: Path to the audio clip file
            begin_time: Beginning time of the clip (in seconds)
            end_time: Ending time of the clip (in seconds)
            index: Index for unique naming

        Returns:
            Dictionary containing transcription results
        """
        print(f"Transcribing audio clip {index}: {os.path.basename(audio_clip_path)}")

        # Verify audio clip exists
        if not os.path.exists(audio_clip_path):
            print(f"❌ Audio clip not found: {audio_clip_path}")
            return {
                'index': index,
                'transcript': "",
                'audio_price': 0.0,
                'begin_time': begin_time,
                'end_time': end_time,
                'error': f"Audio clip not found: {audio_clip_path}"
            }

        try:
            # Get audio duration for cost calculation
            with sf.SoundFile(audio_clip_path) as f:
                audio_duration = f.frames / f.samplerate

            # Generate transcript using GPT-4o-Transcribe
            with open(audio_clip_path, "rb") as audio_file_obj:
                transcript = client.audio.transcriptions.create(
                    model=ASR_MODEL,  # Use configured model
                    file=audio_file_obj,
                    response_format="text",
                    temperature=0.001,
                    prompt="You are a performance reviewer assessing a Dairy Queen drive-thru operator's handling of an order. Create a transcript, noting whether the operator or the customer is speaking."
                )

            # Calculate audio transcription cost
            audio_price = (audio_duration * 0.0012 / 60)  # $0.0012 per minute
            print(f"💰 Audio transcription cost for clip {index}: ${audio_price:.6f}")
            print(f"✅ Transcribed clip {index}: {len(str(transcript))} characters")

            return {
                'index': index,
                'transcript': str(transcript),
                'audio_price': audio_price,
                'begin_time': begin_time,
                'end_time': end_time,
                'audio_duration': audio_duration,
                'clip_path': audio_clip_path
            }

        except Exception as e:
            print(f"❌ Error transcribing audio clip {index}: {e}")
            return {
                'index': index,
                'transcript': "",
                'audio_price': 0.0,
                'begin_time': begin_time,
                'end_time': end_time,
                'error': str(e)
            }