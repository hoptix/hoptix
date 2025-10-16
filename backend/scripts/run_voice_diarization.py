#!/usr/bin/env python3
"""
Executable script to run the voice diarization pipeline.
Processes transaction clips to identify workers based on voice matching.

Usage:
    python run_voice_diarization.py <location_id> <date> [options]

Example:
    python run_voice_diarization.py c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06
    python run_voice_diarization.py --location-id c3607cc3-0f0c-4725-9c42-eb2fdb5e016a --date 2025-10-06 --samples-folder "Cary Voice Samples"
"""

import sys
import os
import argparse
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.voice_diarization_pipeline import voice_diarization_pipeline, process_location_date_range


def validate_date(date_string):
    """Validate that the date string is in YYYY-MM-DD format"""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_uuid(uuid_string):
    """Basic UUID validation"""
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return re.match(uuid_pattern, uuid_string, re.IGNORECASE) is not None


def main():
    """Main function to run the voice diarization pipeline"""
    parser = argparse.ArgumentParser(
        description="Run the voice diarization pipeline for worker identification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single date
  python run_voice_diarization.py c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06

  # Process with custom folders
  python run_voice_diarization.py c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06 \\
      --samples-folder "Cary Voice Samples" \\
      --clips-folder "Clips_2025-10-06_0700"

  # Process a date range
  python run_voice_diarization.py c3607cc3-0f0c-4725-9c42-eb2fdb5e016a \\
      --start-date 2025-10-01 --end-date 2025-10-07
        """
    )

    parser.add_argument(
        'location_id',
        nargs='?',
        help='Location ID (UUID format)'
    )

    parser.add_argument(
        'date',
        nargs='?',
        help='Date in YYYY-MM-DD format (for single date processing)'
    )

    parser.add_argument(
        '--location-id',
        dest='location_id_flag',
        help='Location ID (alternative flag format)'
    )

    parser.add_argument(
        '--date',
        dest='date_flag',
        help='Date in YYYY-MM-DD format (alternative flag format)'
    )

    parser.add_argument(
        '--start-date',
        help='Start date for range processing (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        help='End date for range processing (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--samples-folder',
        help='Google Drive folder name containing voice samples (default: from env)'
    )

    parser.add_argument(
        '--clips-folder',
        help='Google Drive folder name containing transaction clips (default: auto-generated)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually processing'
    )

    args = parser.parse_args()

    # Handle both positional and flag arguments
    location_id = args.location_id or args.location_id_flag
    date = args.date or args.date_flag

    # Check if we're doing range processing
    if args.start_date and args.end_date:
        if not location_id:
            print("❌ Error: Location ID is required for date range processing")
            sys.exit(1)

        if not validate_uuid(location_id):
            print(f"❌ Error: Invalid location_id format: {location_id}")
            print("   Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
            sys.exit(1)

        if not validate_date(args.start_date):
            print(f"❌ Error: Invalid start date format: {args.start_date}")
            print("   Expected format: YYYY-MM-DD")
            sys.exit(1)

        if not validate_date(args.end_date):
            print(f"❌ Error: Invalid end date format: {args.end_date}")
            print("   Expected format: YYYY-MM-DD")
            sys.exit(1)

        # Show what will be done
        print("🚀 Voice Diarization Pipeline - Date Range Processing")
        print("=" * 60)
        print(f"📍 Location ID: {location_id}")
        print(f"📅 Date Range: {args.start_date} to {args.end_date}")
        if args.samples_folder:
            print(f"🎤 Samples Folder: {args.samples_folder}")
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        if args.dry_run:
            print("🔍 DRY RUN MODE - No actual processing will occur")
            print("\nWould process each date in the range with voice diarization")
            return 0

        # Run range processing
        try:
            from pipeline.voice_diarization_pipeline import process_location_date_range

            print("🔄 Starting range processing...")
            result = process_location_date_range(
                location_id=location_id,
                start_date=args.start_date,
                end_date=args.end_date,
                samples_folder=args.samples_folder
            )

            print("\n📊 Range Processing Summary:")
            print(f"   Days Processed: {result['days_processed']}")
            print(f"   Total Updated: {result['total_updated']}")
            print(f"   Total No Match: {result['total_no_match']}")
            print(f"   Total Failures: {result['total_failures']}")

            return 0

        except Exception as e:
            print(f"\n❌ Range processing failed: {e}")
            if args.verbose:
                import traceback
                print("\nFull traceback:")
                traceback.print_exc()
            return 1

    # Single date processing
    if not location_id or not date:
        print("❌ Error: Both location_id and date are required for single date processing")
        print("   Or use --start-date and --end-date for range processing")
        parser.print_help()
        sys.exit(1)

    # Validate inputs
    if not validate_uuid(location_id):
        print(f"❌ Error: Invalid location_id format: {location_id}")
        print("   Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)

    if not validate_date(date):
        print(f"❌ Error: Invalid date format: {date}")
        print("   Expected format: YYYY-MM-DD (e.g., 2025-10-06)")
        sys.exit(1)

    # Show what will be done
    print("🚀 Voice Diarization Pipeline Runner")
    print("=" * 60)
    print(f"📍 Location ID: {location_id}")
    print(f"📅 Date: {date}")
    if args.samples_folder:
        print(f"🎤 Samples Folder: {args.samples_folder}")
    if args.clips_folder:
        print(f"📁 Clips Folder: {args.clips_folder}")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual processing will occur")
        print("\nPipeline steps that would be executed:")
        print("  1. Load TitaNet speaker verification model")
        print("  2. Fetch worker mappings from database")
        print("  3. Build embeddings from voice samples in Google Drive")
        print("  4. Download transaction clips from Google Drive")
        print("  5. Process each clip with voice diarization")
        print("  6. Match speakers to known workers")
        print("  7. Update database with worker assignments")
        print("  8. Generate processing report")
        print("\n✅ Dry run completed successfully")
        return 0

    # Run the pipeline
    try:
        print("🔄 Starting pipeline execution...")
        result = voice_diarization_pipeline(
            location_id=location_id,
            date=date,
            samples_folder=args.samples_folder,
            clips_folder=args.clips_folder
        )

        if result["status"] == "success":
            print("\n🎉 Pipeline completed successfully!")
            print(f"✅ Run ID: {result.get('run_id')}")
            print(f"📊 Results:")
            print(f"   - Processed: {result.get('processed', 0)} clips")
            print(f"   - Updated: {result.get('updated', 0)} transactions")
            print(f"   - No match: {result.get('no_match', 0)} clips")
            print(f"   - Failures: {result.get('failures', 0)} clips")
            return 0
        else:
            print(f"\n⚠️ Pipeline completed with errors: {result.get('message', 'Unknown error')}")
            return 1

    except KeyboardInterrupt:
        print("\n⏹️ Pipeline interrupted by user")
        return 130

    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        if args.verbose:
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)