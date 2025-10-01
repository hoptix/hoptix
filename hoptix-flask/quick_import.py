#!/usr/bin/env python3
"""
Quick import script for specific Google Drive folder
Usage: python quick_import.py <folder_id> <org_id> <location_id> <date>
Example: python quick_import.py 1d997vkf7a6b7wVJxcC99wQY4ZWIQ8QOX org123 loc456 2025-07-15
"""

import sys
import os
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from import_from_specific_folder import import_from_folder_id

def main():
    if len(sys.argv) != 5:
        print("Usage: python quick_import.py <folder_id> <org_id> <location_id> <date>")
        print("Example: python quick_import.py 1d997vkf7a6b7wVJxcC99wQY4ZWIQ8QOX org123 loc456 2025-07-15")
        sys.exit(1)
    
    folder_id = sys.argv[1]
    org_id = sys.argv[2]
    location_id = sys.argv[3]
    run_date = sys.argv[4]
    
    print(f"🚀 Importing from Google Drive folder: {folder_id}")
    print(f"📅 Date: {run_date}")
    print(f"🏢 Org ID: {org_id}")
    print(f"📍 Location ID: {location_id}")
    
    imported_ids = import_from_folder_id(folder_id, org_id, location_id, run_date)
    
    if imported_ids:
        print(f"🎉 Import completed successfully! {len(imported_ids)} videos imported.")
    else:
        print("❌ Import failed or no videos were imported.")

if __name__ == "__main__":
    main()
