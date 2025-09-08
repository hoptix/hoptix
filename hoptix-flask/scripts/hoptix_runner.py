#!/usr/bin/env python3
"""
Hoptix Runner - Single executable script for all video processing operations.

This script provides a unified CLI interface with subcommands for:
- full-pipeline: Import videos from Google Drive and process them
- import: Import videos from Google Drive only
- process: Process uploaded videos only
- setup-database: Initialize database entities

Examples:
    python scripts/hoptix_runner.py full-pipeline --org-id abc123 --location-id def456 --date 2025-08-29
    python scripts/hoptix_runner.py import --org-id abc123 --location-id def456 --date 2025-08-29
    python scripts/hoptix_runner.py process --all
    python scripts/hoptix_runner.py setup-database --org "Dairy Queen" --location "Cary"
"""

import os
import sys
import logging
import argparse

# Add the parent directory to Python path so we can import from hoptix-flask
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from commands.run_full_pipeline import FullPipelineCommand

def setup_logging():
    """Configure logging for the runner."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('hoptix_runner.log'),
            logging.StreamHandler()
        ]
    )

def cmd_full_pipeline(args):
    """Run the full pipeline: import from Google Drive and process videos."""
    command = FullPipelineCommand()
    command.run(args.org_id, args.location_id, args.date)

def cmd_import(args):
    """Import videos from Google Drive only."""
    # TODO: Create ImportCommand class
    print("Import command not yet implemented. Use full-pipeline for now.")
    sys.exit(1)

def cmd_process(args):
    """Process uploaded videos only."""
    # TODO: Create ProcessCommand class
    print("Process command not yet implemented. Use full-pipeline for now.")
    sys.exit(1)

def cmd_setup_database(args):
    """Setup database entities."""
    # TODO: Create SetupDatabaseCommand class
    print("Setup database command not yet implemented.")
    sys.exit(1)

def main():
    """Main entry point with subcommand parsing."""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='Hoptix video processing runner',
        epilog='Use "python scripts/hoptix_runner.py <command> --help" for command-specific help'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    subparsers.required = True
    
    # Full pipeline command
    pipeline_parser = subparsers.add_parser(
        'full-pipeline',
        help='Import videos from Google Drive and process them'
    )
    pipeline_parser.add_argument(
        '--org-id', type=str, required=True,
        help='Organization ID (must exist in database)'
    )
    pipeline_parser.add_argument(
        '--location-id', type=str, required=True,
        help='Location ID (must exist and belong to the organization)'
    )
    pipeline_parser.add_argument(
        '--date', type=str, required=True,
        help='Date in YYYY-MM-DD format - import and process videos from this date'
    )
    pipeline_parser.set_defaults(func=cmd_full_pipeline)
    
    # Import command
    import_parser = subparsers.add_parser(
        'import',
        help='Import videos from Google Drive only'
    )
    import_parser.add_argument(
        '--date', type=str, required=True,
        help='Date in YYYY-MM-DD format - import videos from this date'
    )
    import_parser.set_defaults(func=cmd_import)
    
    # Process command
    process_parser = subparsers.add_parser(
        'process',
        help='Process uploaded videos only'
    )
    process_group = process_parser.add_mutually_exclusive_group(required=True)
    process_group.add_argument('--all', action='store_true', help='Process all uploaded videos')
    process_group.add_argument('--video-id', type=str, help='Process specific video by ID')
    process_parser.set_defaults(func=cmd_process)
    
    # Setup database command
    setup_parser = subparsers.add_parser(
        'setup-database',
        help='Initialize database entities'
    )
    setup_parser.add_argument('--org', type=str, default='Dairy Queen', help='Organization name')
    setup_parser.add_argument('--location', type=str, default='Cary', help='Location name')
    setup_parser.set_defaults(func=cmd_setup_database)
    
    # Parse and execute
    args = parser.parse_args()
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
