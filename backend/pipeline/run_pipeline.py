#!/usr/bin/env python3
"""
Executable script to run the full Hoptix pipeline.
Takes location_id and date as command line arguments.

Usage:
    python run_pipeline.py <location_id> <date>
    
Example:
    python run_pipeline.py c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-08
"""

import sys
import os
import argparse
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.full_pipeline import full_pipeline


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
    """Main function to run the pipeline"""
    parser = argparse.ArgumentParser(
        description="Run the full Hoptix pipeline for a specific location and date",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-08
  python run_pipeline.py --location-id c3607cc3-0f0c-4725-9c42-eb2fdb5e016a --date 2025-10-08
        """
    )
    
    parser.add_argument(
        'location_id',
        help='Location ID (UUID format)'
    )
    
    parser.add_argument(
        'date',
        help='Date in YYYY-MM-DD format'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually running the pipeline'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not validate_uuid(args.location_id):
        print(f"❌ Error: Invalid location_id format: {args.location_id}")
        print("   Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)
    
    if not validate_date(args.date):
        print(f"❌ Error: Invalid date format: {args.date}")
        print("   Expected format: YYYY-MM-DD (e.g., 2025-10-08)")
        sys.exit(1)
    
    # Show what will be done
    print("🚀 Hoptix Pipeline Runner")
    print("=" * 50)
    print(f"📍 Location ID: {args.location_id}")
    print(f"📅 Date: {args.date}")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual processing will occur")
        print("\nPipeline steps that would be executed:")
        print("  1. Check and pull audio from location and date")
        print("  2. Transcribe audio to text")
        print("  3. Split audio into transactions")
        print("  4. Insert transactions into database")
        print("  5. Grade transactions")
        print("  6. Upsert grades into database")
        print("  7. Generate analytics report")
        print("  8. Write clips to Google Drive")
        print("  9. Complete pipeline")
        print("\n✅ Dry run completed successfully")
        return 0
    
    # Run the pipeline
    try:
        print("🔄 Starting pipeline execution...")
        result = full_pipeline(args.location_id, args.date)
        
        if result == "Successfully completed full pipeline":
            print("\n🎉 Pipeline completed successfully!")
            print(f"✅ Result: {result}")
            return 0
        else:
            print(f"\n⚠️ Pipeline completed with message: {result}")
            return 0
            
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
