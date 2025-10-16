# Porter Setup Guide for Voice Diarization

## Quick Setup

### Option 1: Use Environment Variables (Recommended for Cron)

1. **In Porter Dashboard** → Your App → Environment Variables, add:

```
LOCATION_ID=c3607cc3-0f0c-4725-9c42-eb2fdb5e016a
DATE=2025-10-06
```

2. **Run command** (as configured in porter.yaml):
```bash
bash scripts/start_voice_job.sh
```

The script will automatically use the env vars.

---

### Option 2: Pass as Command Arguments

1. **In Porter Dashboard** → Configure Cron Job

2. **Override the run command** to:
```bash
bash scripts/start_voice_job.sh c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06
```

---

### Option 3: Dynamic Date (Run for Today)

1. **Set only LOCATION_ID** as environment variable:
```
LOCATION_ID=c3607cc3-0f0c-4725-9c42-eb2fdb5e016a
```

2. **Use the daily runner script**:
```bash
bash scripts/run_voice_today.sh
```

This automatically uses today's date.

---

## Required Environment Variables

### Core API Keys (Required)

```bash
AAI_API_KEY=your-assemblyai-key
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
GOOGLE_DRIVE_CREDENTIALS={"type": "service_account", "project_id": "...", ...}
```

### Voice Diarization Config (Required)

```bash
VOICE_SAMPLES_FOLDER=Cary Voice Samples
VOICE_CLIPS_FOLDER=Clips_2025-10-06_0700
```

Note: `VOICE_CLIPS_FOLDER` can be auto-generated based on date if not provided.

### Job Parameters (Choose one approach)

**Approach A - Static (set in Porter env vars)**:
```bash
LOCATION_ID=c3607cc3-0f0c-4725-9c42-eb2fdb5e016a
DATE=2025-10-06
```

**Approach B - Dynamic (pass via command)**:
- Don't set these as env vars
- Pass them in the run command instead

### Optional Configuration

```bash
# Performance tuning
VOICE_DIARIZATION_THRESHOLD=0.2
VOICE_PARALLEL_WORKERS=5
MAX_JOB_DURATION=21600

# Monitoring/alerting
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
NOTIFY_JOB_START=true
```

---

## Porter Dashboard Configuration

### 1. Deploy the Application

```bash
# From repo root
git add .
git commit -m "Add voice diarization with Pydantic fixes"
git push
```

Porter will automatically deploy based on `porter.yaml`.

### 2. Configure Cron Schedule

In Porter Dashboard:
1. Go to your voice-diarization-job
2. Click "Configure Cron"
3. Set schedule: `0 3 * * *` (3 AM daily)
4. Choose command option:

**Option A - Use env vars**:
- Leave command as default: `bash scripts/start_voice_job.sh`
- Make sure `LOCATION_ID` and `DATE` are set in env vars

**Option B - Override command**:
- Custom command: `bash scripts/start_voice_job.sh c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06`

**Option C - Dynamic date**:
- Custom command: `bash scripts/run_voice_today.sh c3607cc3-0f0c-4725-9c42-eb2fdb5e016a`

### 3. Manual Job Trigger

To run the job manually:

1. Go to Jobs tab
2. Click "Run Job"
3. Either:
   - Use default command (if env vars are set)
   - Or override: `bash scripts/start_voice_job.sh <location_id> <date>`

---

## Verifying Setup

### Check Logs

After deployment, check Porter logs for:

```
✓ Applied Pydantic v1/v2 compatibility patch
✓ Pydantic version: 2.x.x
✓ Supabase import successful
✓ Lightweight database module import successful
```

### Test Import Compatibility

Manually trigger a test run:

```bash
bash scripts/start_voice_job.sh
```

Should show clear error if LOCATION_ID/DATE are missing, with usage instructions.

---

## Troubleshooting

### "LOCATION_ID and DATE must be provided"

**Fix**: Either set env vars in Porter dashboard OR pass as command args.

### "ImportError: cannot import name 'with_config'"

**Status**: This should be fixed by the compatibility patches.

**Verify**: Check logs for:
```
✓ Applied Pydantic v1/v2 compatibility patch
```

If still failing, the lightweight database module will automatically take over.

### Job fails immediately

**Check**: Run logs should show:
```
🚀 Starting Voice Diarization Job with compatibility fixes
📋 Testing Pydantic compatibility...
```

If you don't see this, the startup script isn't running correctly.

---

## Complete Example

### Porter Environment Variables

Set these in Porter Dashboard → Environment Variables:

```bash
# API Keys
AAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GOOGLE_DRIVE_CREDENTIALS={"type": "service_account", "project_id": "xxx", ...}

# Voice Config
VOICE_SAMPLES_FOLDER=Cary Voice Samples

# Job Parameters (if using env var approach)
LOCATION_ID=c3607cc3-0f0c-4725-9c42-eb2fdb5e016a
DATE=2025-10-06

# Optional - Monitoring
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Cron Configuration

**Schedule**: `0 3 * * *` (every day at 3 AM)

**Command**: `bash scripts/start_voice_job.sh` (uses env vars)

OR

**Command**: `bash scripts/run_voice_today.sh` (dynamic date, only needs LOCATION_ID env var)

---

## Summary

✅ **Simplest setup** (recommended):
1. Set `LOCATION_ID` as env var in Porter
2. Use cron command: `bash scripts/run_voice_today.sh`
3. Runs automatically for current date every day

✅ **Most flexible setup**:
1. Don't set LOCATION_ID/DATE as env vars
2. Configure each cron job with: `bash scripts/start_voice_job.sh <location_id> <date>`
3. Can have different schedules for different locations

✅ **Static date setup**:
1. Set both `LOCATION_ID` and `DATE` as env vars
2. Use default command: `bash scripts/start_voice_job.sh`
3. Update DATE manually when needed