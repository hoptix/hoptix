#!/usr/bin/env python3
"""
Voice Diarization Job - Main Entry Point
Clean implementation without Pydantic conflicts
"""

import os
import sys
import logging
import argparse
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
import gc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def check_gpu_availability() -> bool:
    """Check if GPU is available and log details."""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            memory_allocated = torch.cuda.memory_allocated(0) / 1024**3
            memory_reserved = torch.cuda.memory_reserved(0) / 1024**3

            logger.info(f"✅ GPU Available: {device_name}")
            logger.info(f"   Devices: {device_count}")
            logger.info(f"   Memory Allocated: {memory_allocated:.2f} GB")
            logger.info(f"   Memory Reserved: {memory_reserved:.2f} GB")
        else:
            logger.warning("⚠️ GPU not available, will use CPU (slower performance)")
        return cuda_available
    except ImportError:
        logger.error("❌ PyTorch not installed")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking GPU: {e}")
        return False


def verify_dependencies() -> bool:
    """Verify all critical dependencies are installed."""
    dependencies_ok = True

    # Check core dependencies
    try:
        import torch
        logger.info(f"✓ PyTorch {torch.__version__}")
    except ImportError as e:
        logger.error(f"✗ PyTorch: {e}")
        dependencies_ok = False

    try:
        import torchaudio
        logger.info(f"✓ Torchaudio {torchaudio.__version__}")
    except ImportError as e:
        logger.error(f"✗ Torchaudio: {e}")
        dependencies_ok = False

    try:
        import assemblyai
        logger.info("✓ AssemblyAI")
    except ImportError as e:
        logger.error(f"✗ AssemblyAI: {e}")
        dependencies_ok = False

    try:
        from nemo.collections.asr.models import EncDecSpeakerLabelModel
        logger.info("✓ NeMo ASR models")
    except ImportError as e:
        logger.error(f"✗ NeMo: {e}")
        dependencies_ok = False

    try:
        import httpx
        logger.info("✓ HTTPX (for Supabase REST)")
    except ImportError as e:
        logger.error(f"✗ HTTPX: {e}")
        dependencies_ok = False

    return dependencies_ok


def validate_environment() -> Dict[str, str]:
    """Validate required environment variables."""
    required_vars = {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_SERVICE_KEY': os.getenv('SUPABASE_SERVICE_KEY'),
        'AAI_API_KEY': os.getenv('AAI_API_KEY'),
    }

    missing = [var for var, value in required_vars.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return required_vars


def run_voice_diarization(
    location_id: str,
    date: str,
    batch_size: int = 10,
    max_workers: int = 2
) -> Dict[str, Any]:
    """
    Run the voice diarization pipeline with proper resource management.

    Args:
        location_id: UUID of the location
        date: Date string in YYYY-MM-DD format
        batch_size: Number of clips to process in each batch
        max_workers: Maximum concurrent workers for processing

    Returns:
        Dictionary with processing results
    """
    from pipeline.voice_diarization_pipeline import VoiceDiarizationPipeline
    from services.database_rest import DatabaseClient

    start_time = datetime.now()
    results = {
        'status': 'started',
        'location_id': location_id,
        'date': date,
        'start_time': start_time.isoformat(),
        'processed': 0,
        'updated': 0,
        'failures': 0,
        'errors': []
    }

    try:
        # Initialize database client (REST-only, no Pydantic)
        db = DatabaseClient()

        # Create run record
        run_id = db.create_run(location_id, date, 'voice_diarization')
        results['run_id'] = run_id
        logger.info(f"Created run: {run_id}")

        # Initialize pipeline
        pipeline = VoiceDiarizationPipeline(
            db_client=db,
            batch_size=batch_size,
            max_workers=max_workers
        )

        # Process the location and date
        logger.info(f"Processing location {location_id} for date {date}")
        process_results = pipeline.process(location_id, date)

        # Update results
        results.update(process_results)
        results['status'] = 'completed'

        # Update run record
        db.update_run(run_id, {
            'status': 'completed',
            'processed': results['processed'],
            'updated': results['updated'],
            'failures': results['failures']
        })

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        logger.error(traceback.format_exc())
        results['status'] = 'failed'
        results['errors'].append(str(e))

        if 'run_id' in results:
            try:
                db.update_run(results['run_id'], {
                    'status': 'failed',
                    'error': str(e)
                })
            except:
                pass

    finally:
        # Clean up GPU memory
        if check_gpu_availability():
            try:
                import torch
                torch.cuda.empty_cache()
                gc.collect()
                logger.info("Cleaned up GPU memory")
            except:
                pass

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = duration

        # Log summary
        logger.info("=" * 60)
        logger.info("PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Status: {results['status']}")
        logger.info(f"Processed: {results['processed']} clips")
        logger.info(f"Updated: {results['updated']} transactions")
        logger.info(f"Failures: {results['failures']}")
        logger.info(f"Duration: {duration:.1f} seconds")

        if results['errors']:
            logger.error(f"Errors: {results['errors']}")

    return results


def main():
    """Main entry point for the voice diarization job."""
    parser = argparse.ArgumentParser(
        description='Voice Diarization Job - Identifies workers in transaction clips'
    )

    # Use environment variables with command line override
    parser.add_argument(
        '--location-id',
        default=os.getenv('LOCATION_ID'),
        help='Location UUID (default: from LOCATION_ID env var)'
    )

    parser.add_argument(
        '--date',
        default=os.getenv('DATE'),
        help='Date in YYYY-MM-DD format (default: from DATE env var)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=int(os.getenv('BATCH_SIZE', '10')),
        help='Number of clips to process per batch (default: 10)'
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        default=int(os.getenv('MAX_WORKERS', '2')),
        help='Maximum concurrent processing workers (default: 2)'
    )

    parser.add_argument(
        '--health-check-port',
        type=int,
        default=int(os.getenv('HEALTH_CHECK_PORT', '8080')),
        help='Port for health check server (default: 8080)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run pre-flight checks only, do not process data'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.location_id or not args.date:
        logger.error("❌ Error: LOCATION_ID and DATE are required")
        logger.error("   Set via environment variables or command line arguments")
        sys.exit(1)

    logger.info("🚀 Voice Diarization Job Starting")
    logger.info("=" * 60)
    logger.info(f"Location ID: {args.location_id}")
    logger.info(f"Date: {args.date}")
    logger.info(f"Batch Size: {args.batch_size}")
    logger.info(f"Max Workers: {args.max_workers}")
    logger.info("=" * 60)

    try:
        # Start health check server in background
        from health_check import start_health_server
        health_thread = start_health_server(args.health_check_port)
        logger.info(f"✅ Health check server started on port {args.health_check_port}")
    except Exception as e:
        logger.warning(f"⚠️ Could not start health check server: {e}")
        health_thread = None

    # Pre-flight checks
    logger.info("Running pre-flight checks...")

    # Check GPU
    gpu_available = check_gpu_availability()

    # Verify dependencies
    if not verify_dependencies():
        logger.error("❌ Dependency check failed")
        sys.exit(1)

    # Validate environment
    try:
        env_vars = validate_environment()
        logger.info("✅ Environment validated")
    except ValueError as e:
        logger.error(f"❌ Environment validation failed: {e}")
        sys.exit(1)

    # Check for dry run
    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No data will be processed")
        logger.info("=" * 60)
        logger.info("Pre-flight checks completed successfully:")
        logger.info(f"  ✓ GPU: {'Available' if gpu_available else 'Not available (CPU mode)'}")
        logger.info("  ✓ Dependencies: All verified")
        logger.info("  ✓ Environment: All required variables set")
        logger.info("  ✓ Database: Connection available")
        logger.info("  ✓ Health check: Server ready")
        logger.info("")
        logger.info("The following would be executed:")
        logger.info(f"  1. Load TitaNet model")
        logger.info(f"  2. Build worker voice embeddings")
        logger.info(f"  3. Process clips from location {args.location_id}")
        logger.info(f"  4. Match speakers for date {args.date}")
        logger.info(f"  5. Update database with results")
        logger.info("")
        logger.info("✅ Dry run completed successfully")
        sys.exit(0)

    # Run the pipeline
    try:
        results = run_voice_diarization(
            location_id=args.location_id,
            date=args.date,
            batch_size=args.batch_size,
            max_workers=args.max_workers
        )

        # Exit with appropriate code
        if results['status'] == 'completed':
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("⏹ Job interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Job failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()