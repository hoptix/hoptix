# Cut Transaction Audio Script

This script processes a long WAV file from your Downloads folder, uploads it to Google Drive, cuts individual transaction clips, and updates the database with Google Drive links.

## Features

- ✅ Downloads WAV file from `~/Downloads` folder
- ✅ Uploads main WAV to Google Drive (`Run_{run_id}_MainAudio` folder)
- ✅ Cuts individual transaction clips using anchor mapping
- ✅ Uploads clips to Google Drive (`Run_{run_id}_Clips` folder)
- ✅ Updates transaction records with Google Drive share links
- ✅ Uses temporary directory for processing (auto-cleanup)

## Usage

```bash
# Set environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"

# Run the script
python3 services/cut_tx_audio_supabase.py \
    --wav-filename "long_audio_recording.wav" \
    --anchor-started-at "2025-10-01T10:29:27.559790+00:00" \
    --anchor-wav "03:45:57" \
    --run-id "your-run-uuid-here" \
    --limit 10
```

## Parameters

- `--wav-filename`: Name of the WAV file in your Downloads folder
- `--anchor-started-at`: ISO8601 timestamp of a known point in the audio
- `--anchor-wav`: Time in the WAV file where that timestamp occurs (HH:MM:SS format)
- `--run-id`: UUID of the run to process transactions for
- `--limit`: Optional limit on number of transactions to process (0 = no limit)

## Example

If you have a 2-hour WAV file and you know that at 03:45:57 in the audio, the timestamp was 2025-10-01T10:29:27.559790+00:00, the script will:

1. Find `long_audio_recording.wav` in your Downloads
2. Upload it to Google Drive in folder `Run_{run_id}_MainAudio`
3. Calculate the mapping: T0 = 2025-10-01T10:29:27.559790+00:00 - 03:45:57
4. For each transaction, calculate the audio position and cut a clip
5. Upload each clip to Google Drive in folder `Run_{run_id}_Clips`
6. Update each transaction record with the Google Drive share link

## Output

The script will:
- Create organized folders in Google Drive
- Generate shareable links for each clip
- Update the `transactions` table with:
  - `s3_key`: Google Drive share link
  - `clip_s3_url`: Local processing path (for reference)

## Requirements

- FFmpeg installed and in PATH
- Google Drive API credentials configured
- Supabase credentials in environment variables
- WAV file in your Downloads folder
