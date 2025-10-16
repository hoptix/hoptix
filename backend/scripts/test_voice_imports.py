#!/usr/bin/env python3
"""
Test script to verify voice diarization dependencies are properly installed
"""

import sys
import traceback

def test_imports():
    """Test all critical imports for voice diarization"""

    results = []

    # Test PyTorch
    try:
        import torch
        results.append(f"✅ PyTorch: {torch.__version__}")
        results.append(f"   CUDA available: {torch.cuda.is_available()}")
    except Exception as e:
        results.append(f"❌ PyTorch: {e}")

    # Test torchaudio
    try:
        import torchaudio
        results.append(f"✅ Torchaudio: {torchaudio.__version__}")
        # Test torchaudio functionality
        dummy_tensor = torch.randn(1, 16000)
        import torchaudio.transforms as T
        resampler = T.Resample(16000, 8000)
        resampled = resampler(dummy_tensor)
        results.append(f"   Torchaudio transforms: OK")
    except Exception as e:
        results.append(f"❌ Torchaudio: {e}")

    # Test NeMo
    try:
        from nemo.collections.asr.models import EncDecSpeakerLabelModel
        results.append(f"✅ NeMo ASR models: OK")
    except Exception as e:
        results.append(f"❌ NeMo ASR models: {e}")

    # Test voice processing libraries
    try:
        from pydub import AudioSegment
        results.append(f"✅ Pydub: OK")
    except Exception as e:
        results.append(f"❌ Pydub: {e}")

    try:
        import assemblyai as aai
        results.append(f"✅ AssemblyAI: OK")
    except Exception as e:
        results.append(f"❌ AssemblyAI: {e}")

    try:
        import librosa
        results.append(f"✅ Librosa: {librosa.__version__}")
    except Exception as e:
        results.append(f"❌ Librosa: {e}")

    # Test Pydantic version
    try:
        import pydantic
        results.append(f"✅ Pydantic: {pydantic.__version__}")
        from pydantic import TypeAdapter
        results.append(f"   TypeAdapter: OK")
    except Exception as e:
        results.append(f"❌ Pydantic: {e}")

    # Test supabase
    try:
        from supabase import create_client
        results.append(f"✅ Supabase: OK")
    except Exception as e:
        results.append(f"❌ Supabase: {e}")

    # Test voice diarization pipeline
    try:
        from pipeline.voice_diarization_pipeline import voice_diarization_pipeline
        results.append(f"✅ Voice diarization pipeline: OK")
    except Exception as e:
        results.append(f"❌ Voice diarization pipeline: {e}")
        # Show traceback for pipeline import failures
        results.append("   Traceback:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                results.append(f"   {line}")

    # Test voice diarization service
    try:
        from services.voice_diarization import VoiceDiarization
        results.append(f"✅ Voice diarization service: OK")
    except Exception as e:
        results.append(f"❌ Voice diarization service: {e}")

    return results


def main():
    """Main test function"""
    print("=" * 60)
    print("Voice Diarization Dependencies Test")
    print("=" * 60)
    print()

    print("Python:", sys.version)
    print()

    results = test_imports()

    for result in results:
        print(result)

    print()
    print("=" * 60)

    # Check if all tests passed
    failures = [r for r in results if r.startswith("❌")]
    if failures:
        print(f"⚠️ {len(failures)} test(s) failed")
        return 1
    else:
        print("✅ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)