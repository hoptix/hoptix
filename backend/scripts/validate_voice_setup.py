#!/usr/bin/env python3
"""
Validation script to check voice diarization setup before running.
Run this before the main job to catch configuration issues early.
"""

import os
import sys
import logging
from typing import Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_environment_variables() -> Tuple[bool, str]:
    """Check all required environment variables are set."""
    required_vars = {
        "AAI_API_KEY": "AssemblyAI API key for transcription",
        "SUPABASE_URL": "Supabase project URL",
        "SUPABASE_SERVICE_KEY": "Supabase service key",
        "GOOGLE_DRIVE_CREDENTIALS": "Google Drive OAuth credentials JSON",
        "VOICE_SAMPLES_FOLDER": "Google Drive folder name with voice samples",
        "VOICE_CLIPS_FOLDER": "Google Drive folder name with transaction clips",
    }

    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  - {var}: {description}")

    if missing:
        return False, f"Missing environment variables:\n" + "\n".join(missing)

    return True, "All environment variables are set"


def check_python_dependencies() -> Tuple[bool, str]:
    """Check all required Python packages are installed."""
    errors = []

    # Check core dependencies
    try:
        import torch
        if not torch.cuda.is_available():
            errors.append("CUDA not available - GPU support required")
    except ImportError:
        errors.append("PyTorch not installed")

    try:
        from nemo.collections.asr.models import EncDecSpeakerLabelModel
    except ImportError:
        errors.append("NeMo not installed - required for TitaNet")

    try:
        from pydub import AudioSegment
    except ImportError:
        errors.append("pydub not installed - required for audio processing")

    try:
        import assemblyai
    except ImportError:
        errors.append("assemblyai not installed - required for transcription")

    try:
        from supabase import create_client
    except ImportError:
        errors.append("supabase not installed - required for database")

    if errors:
        return False, "Dependency issues:\n  - " + "\n  - ".join(errors)

    return True, "All Python dependencies are installed"


def check_google_drive_access() -> Tuple[bool, str]:
    """Check Google Drive authentication and folder access."""
    try:
        from services.gdrive import GoogleDriveClient

        gdrive = GoogleDriveClient()

        samples_folder = os.getenv("VOICE_SAMPLES_FOLDER")
        clips_folder = os.getenv("VOICE_CLIPS_FOLDER")

        if samples_folder:
            folder_id = gdrive.get_folder_id_from_name(samples_folder)
            if not folder_id:
                return False, f"Cannot find samples folder '{samples_folder}' in Google Drive"

            files = gdrive.list_media_files_shared_with_me(folder_id)
            wav_files = [f for f in files if f['name'].endswith('.wav')]
            if not wav_files:
                return False, f"No WAV files found in samples folder '{samples_folder}'"

            logger.info(f"  ✓ Found {len(wav_files)} voice samples")

        if clips_folder:
            folder_id = gdrive.get_folder_id_from_name(clips_folder)
            if not folder_id:
                logger.warning(f"Cannot find clips folder '{clips_folder}' - will be checked at runtime")
            else:
                files = gdrive.list_media_files_shared_with_me(folder_id)
                clip_files = [f for f in files if f['name'].startswith('tx_')]
                logger.info(f"  ✓ Found {len(clip_files)} transaction clips")

        return True, "Google Drive access verified"

    except Exception as e:
        return False, f"Google Drive access error: {e}"


def check_database_access() -> Tuple[bool, str]:
    """Check Supabase database connectivity and data."""
    try:
        from services.database import Supa

        db = Supa()

        # Check workers table
        workers = db.client.table("workers").select("id, legal_name").limit(1).execute()
        if not workers.data:
            return False, "No workers found in database"

        logger.info(f"  ✓ Database connected, workers table accessible")

        # Check graded_rows_filtered view exists
        test = db.client.table("graded_rows_filtered").select("transaction_id").limit(1).execute()
        logger.info(f"  ✓ graded_rows_filtered view accessible")

        return True, "Database access verified"

    except Exception as e:
        return False, f"Database access error: {e}"


def check_assemblyai_api() -> Tuple[bool, str]:
    """Check AssemblyAI API key validity."""
    try:
        import assemblyai as aai
        api_key = os.getenv("AAI_API_KEY")

        if not api_key:
            return False, "AAI_API_KEY not set"

        aai.settings.api_key = api_key

        # We can't fully test without making a real API call, but at least check format
        if len(api_key) < 20:
            return False, "AAI_API_KEY appears invalid (too short)"

        return True, "AssemblyAI API key configured"

    except Exception as e:
        return False, f"AssemblyAI setup error: {e}"


def check_gpu_availability() -> Tuple[bool, str]:
    """Check GPU/CUDA availability."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False, "CUDA not available - GPU required for TitaNet"

        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9

        logger.info(f"  ✓ GPU: {gpu_name}")
        logger.info(f"  ✓ Memory: {gpu_memory:.1f} GB")

        if gpu_memory < 4:
            logger.warning("  ⚠️ Low GPU memory - may have issues with large batches")

        return True, f"GPU available: {gpu_name}"

    except Exception as e:
        return False, f"GPU check error: {e}"


def main():
    """Run all validation checks."""
    print("\n🔍 Voice Diarization Setup Validation\n")
    print("=" * 50)

    checks = [
        ("Environment Variables", check_environment_variables),
        ("Python Dependencies", check_python_dependencies),
        ("GPU Availability", check_gpu_availability),
        ("Google Drive Access", check_google_drive_access),
        ("Database Access", check_database_access),
        ("AssemblyAI API", check_assemblyai_api),
    ]

    all_passed = True

    for name, check_func in checks:
        print(f"\n📋 {name}:")
        try:
            passed, message = check_func()
            if passed:
                print(f"  ✅ {message}")
            else:
                print(f"  ❌ {message}")
                all_passed = False
        except Exception as e:
            print(f"  ❌ Check failed: {e}")
            all_passed = False

    print("\n" + "=" * 50)

    if all_passed:
        print("✅ All checks passed! Ready to run voice diarization.")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())