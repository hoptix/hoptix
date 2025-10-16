"""
Voice Diarization Pipeline for processing transaction clips and identifying workers.
Main orchestration module for the voice-based worker identification system.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import gc
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from services.database import Supa
from services.voice_diarization import VoiceDiarization
from utils.helpers import get_memory_usage, log_memory_usage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

db = Supa()


def voice_diarization_pipeline(
    location_id: str,
    date: str,
    samples_folder: Optional[str] = None,
    clips_folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the voice diarization pipeline for a specific location and date.

    Args:
        location_id: UUID of the location
        date: Date in YYYY-MM-DD format
        samples_folder: Override for voice samples folder name (default from env)
        clips_folder: Override for clips folder name (default from env)

    Returns:
        Dictionary with processing results and statistics
    """
    TOTAL_STEPS = 5

    # Get location name
    location_name = db.get_location_name(location_id)
    if not location_name:
        error_msg = f"Location ID {location_id} not found in database"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "processed": 0,
            "updated": 0
        }

    # Get folder names from environment or use overrides
    if not samples_folder:
        samples_folder = os.getenv("VOICE_SAMPLES_FOLDER", "Cary Voice Samples")

    if not clips_folder:
        clips_folder = os.getenv("VOICE_CLIPS_FOLDER", f"Clips_{date}_0700")

    initial_memory = get_memory_usage()

    logger.info(f"🚀 Starting voice diarization pipeline for {location_name} on {date}")
    logger.info(f"📊 Initial memory usage: {initial_memory:.1f} MB")
    logger.info(f"📁 Samples folder (Google Drive): {samples_folder}")
    logger.info(f"📁 Clips folder (Google Drive): {clips_folder}")

    # Initialize voice diarization service
    log_memory_usage("Initializing voice diarization service", 1, TOTAL_STEPS)
    voice_service = VoiceDiarization()

    # Create or get run record
    log_memory_usage("Creating run record", 2, TOTAL_STEPS)
    run_id = initialize_voice_pipeline(location_id, date)

    try:
        # Process all clips in the folder
        log_memory_usage(f"Processing clips from {clips_folder}", 3, TOTAL_STEPS)

        results = voice_service.process_clips_batch(
            clips_folder=clips_folder,
            samples_folder=samples_folder
        )

        logger.info(f"✅ Processing complete:")
        logger.info(f"   - Total clips: {results['processed']}")
        logger.info(f"   - Updated: {results['updated']}")
        logger.info(f"   - No match: {results['no_match']}")
        logger.info(f"   - Failures: {results['failures']}")

        # Force garbage collection after processing
        gc.collect()
        log_memory_usage("Processing completed, memory cleaned", 4, TOTAL_STEPS)

        # Update run status
        log_memory_usage("Updating run status", 5, TOTAL_STEPS)
        complete_voice_pipeline(run_id, results)

        final_memory = get_memory_usage()
        logger.info(f"\n🎉 Successfully completed voice diarization pipeline!")
        logger.info(f"📊 Memory usage: {initial_memory:.1f} MB → {final_memory:.1f} MB")
        logger.info(f"📈 Memory efficiency: {((final_memory - initial_memory) / initial_memory * 100):+.1f}%")

        return {
            "status": "success",
            "run_id": run_id,
            "location": location_name,
            "date": date,
            **results
        }

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)

        # Mark run as failed
        if run_id:
            fail_voice_pipeline(run_id, str(e))

        return {
            "status": "error",
            "message": str(e),
            "run_id": run_id if 'run_id' in locals() else None,
            "processed": 0,
            "updated": 0
        }


def initialize_voice_pipeline(location_id: str, date: str) -> str:
    """
    Initialize the pipeline by creating a run record.

    Args:
        location_id: UUID of the location
        date: Date string

    Returns:
        Run ID for tracking
    """
    # Insert run record with voice-specific type
    run_data = {
        "location_id": location_id,
        "date": date,
        "status": "processing",
        "pipeline_type": "voice_diarization",
        "started_at": datetime.utcnow().isoformat()
    }

    response = db.client.table("runs").insert(run_data).execute()

    if response.data and len(response.data) > 0:
        run_id = response.data[0]["id"]
        logger.info(f"Created run ID: {run_id}")
        return run_id
    else:
        # Fallback: use the standard insert_run method
        return db.insert_run(location_id, date)


def complete_voice_pipeline(run_id: str, results: Dict[str, int]):
    """
    Mark the pipeline run as complete and store results.

    Args:
        run_id: Run ID to update
        results: Processing results dictionary
    """
    update_data = {
        "status": "complete",
        "completed_at": datetime.utcnow().isoformat(),
        "metadata": results  # Store processing statistics
    }

    response = db.client.table("runs").update(update_data).eq("id", run_id).execute()

    if response.data:
        logger.info(f"Run {run_id} marked as complete")
    else:
        logger.warning(f"Failed to update run {run_id} status")


def fail_voice_pipeline(run_id: str, error_message: str):
    """
    Mark the pipeline run as failed.

    Args:
        run_id: Run ID to update
        error_message: Error description
    """
    update_data = {
        "status": "failed",
        "completed_at": datetime.utcnow().isoformat(),
        "error": error_message
    }

    try:
        response = db.client.table("runs").update(update_data).eq("id", run_id).execute()
        if response.data:
            logger.info(f"Run {run_id} marked as failed")
    except Exception as e:
        logger.error(f"Failed to update run status: {e}")


def process_location_date_range(
    location_id: str,
    start_date: str,
    end_date: str,
    samples_folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process multiple dates for a location.

    Args:
        location_id: UUID of the location
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        samples_folder: Override for voice samples folder

    Returns:
        Summary of all processing results
    """
    from datetime import datetime, timedelta

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    results_summary = {
        "location_id": location_id,
        "start_date": start_date,
        "end_date": end_date,
        "days_processed": 0,
        "total_updated": 0,
        "total_no_match": 0,
        "total_failures": 0,
        "daily_results": []
    }

    current_date = start
    while current_date <= end:
        date_str = current_date.strftime("%Y-%m-%d")
        logger.info(f"\n📅 Processing date: {date_str}")

        result = voice_diarization_pipeline(
            location_id=location_id,
            date=date_str,
            samples_folder=samples_folder
        )

        results_summary["daily_results"].append({
            "date": date_str,
            **result
        })

        if result["status"] == "success":
            results_summary["days_processed"] += 1
            results_summary["total_updated"] += result.get("updated", 0)
            results_summary["total_no_match"] += result.get("no_match", 0)
            results_summary["total_failures"] += result.get("failures", 0)

        current_date += timedelta(days=1)

    return results_summary


if __name__ == "__main__":
    # Example usage for testing
    import argparse

    parser = argparse.ArgumentParser(description="Voice Diarization Pipeline")
    parser.add_argument("location_id", help="Location UUID")
    parser.add_argument("date", help="Date in YYYY-MM-DD format")
    parser.add_argument("--samples-folder", help="Voice samples folder name")
    parser.add_argument("--clips-folder", help="Clips folder name")

    args = parser.parse_args()

    result = voice_diarization_pipeline(
        location_id=args.location_id,
        date=args.date,
        samples_folder=args.samples_folder,
        clips_folder=args.clips_folder
    )

    print(f"\nPipeline result: {result}")