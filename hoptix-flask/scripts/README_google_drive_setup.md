# Google Drive Integration Setup

This guide explains how to set up Google Drive integration to import videos from the "Hoptix Video Server" shared drive.

## Prerequisites

1. Access to the "Hoptix Video Server" shared drive
2. Google Cloud Project with Drive API enabled
3. Service account or OAuth credentials

## Setup Steps

### 1. Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Drive API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

### 2. Create Credentials

#### Option A: Service Account (Recommended for server)
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in service account details
4. Download the JSON key file
5. Rename it to `credentials.json` and place in the flask root directory
6. Share the "Hoptix Video Server" drive with the service account email

#### Option B: OAuth 2.0 (For local development)
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Desktop application"
4. Download the JSON file
5. Rename it to `credentials.json` and place in the flask root directory

### 3. Install Dependencies

```bash
cd hoptix-flask
pip install -r requirements.txt
```

### 4. Test the Connection

```bash
python scripts/import_from_gdrive.py --run-date 2025-08-29 --max-files 1
```

This will:
- Authenticate with Google Drive
- Find the shared drive and folder
- Filter videos for the specified date (2025-08-29)
- Import 1 video file to the database (without downloading)

### 5. Import Videos

**Note: The `--run-date` parameter is required. Only videos matching this exact date will be imported.**

#### Import metadata only (fast):
```bash
python scripts/import_from_gdrive.py --run-date 2025-08-29
```

#### Import and download to S3:
```bash
python scripts/import_from_gdrive.py --run-date 2025-08-29 --download-to-s3
```

#### Import with file limit for testing:
```bash
python scripts/import_from_gdrive.py --run-date 2025-08-29 --max-files 3
```

## File Structure Expected

The script expects video files in the "DQ Cary" folder of the "Hoptix Video Server" shared drive.

Video files should ideally follow the naming pattern:
- `DT_File20250817120001000.avi` (timestamp embedded)
- Format: `DT_FileYYYYMMDDHHMMSSsss` where `sss` is milliseconds

If files don't follow this pattern, the script will use the file creation time or current time as fallback.

## Configuration

Environment variables you can set:

- `S3_PREFIX`: S3 key prefix for uploaded videos (default: "gdrive/dq_cary")
- `GDRIVE_VIDEO_DURATION_SEC`: Default video duration in seconds (default: 3600 = 1 hour)

## Troubleshooting

### Authentication Issues
- Make sure `credentials.json` is in the correct location
- For service accounts, ensure the shared drive is shared with the service account email
- For OAuth, you'll need to go through the browser authentication flow

### Permission Issues
- Ensure you have access to the "Hoptix Video Server" shared drive
- Verify the "DQ Cary" folder exists and you have read permissions

### File Not Found
- Check that video files exist in the expected folder
- Verify file permissions allow reading

## Processing Imported Videos

After importing videos, process them with:

```bash
# Process all uploaded videos
python -m worker.runner

# Or process once
python -m worker.run_once
```

The processing pipeline will:
1. Transcribe audio
2. Split into transactions
3. Grade transactions
4. Store results in database

Note: Video subclips are no longer generated as per the recent update.
