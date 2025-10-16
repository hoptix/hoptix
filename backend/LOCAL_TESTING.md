# Local Testing Guide for Voice Diarization

Test the voice diarization system locally before deploying to Porter.

## Method 1: Test Python Scripts Directly (Fastest - 30 seconds)

Test just the import fixes without GPU:

```bash
cd backend

# Test Pydantic compatibility
python scripts/test_pydantic_imports.py

# Test with compatibility patch
python scripts/fix_pydantic_compat.py --test

# Test the main script (will fail without GPU but tests imports)
python scripts/run_voice_diarization.py --help
```

**Expected output**: Scripts should import successfully and show help text.

---

## Method 2: Build Docker Image Locally (5-10 minutes)

Build the exact image that will be deployed:

```bash
cd /Users/aarav/Desktop/Aarav/Miscellaneous/Projects/hoptix

# Build the image
docker build -f backend/Dockerfile.gpu-pytorch-base -t voice-diarization-test .

# Expected: Build succeeds and runs test_pydantic_imports.py during build
```

**Check build logs for**:
- ✓ Pydantic compatibility test
- ✓ Import tests
- No ImportError messages

---

## Method 3: Run Docker Container Locally (2-3 minutes)

Test the full container (CPU only - no GPU needed for testing imports):

### A. Test Startup Script

```bash
# Set environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-key"
export GOOGLE_DRIVE_CREDENTIALS='{"type": "service_account", ...}'
export AAI_API_KEY="your-assemblyai-key"
export VOICE_SAMPLES_FOLDER="Cary Voice Samples"

# Test with env vars
docker run --rm \
  -e SUPABASE_URL="$SUPABASE_URL" \
  -e SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" \
  -e GOOGLE_DRIVE_CREDENTIALS="$GOOGLE_DRIVE_CREDENTIALS" \
  -e AAI_API_KEY="$AAI_API_KEY" \
  -e VOICE_SAMPLES_FOLDER="$VOICE_SAMPLES_FOLDER" \
  -e LOCATION_ID="c3607cc3-0f0c-4725-9c42-eb2fdb5e016a" \
  -e DATE="2025-10-06" \
  voice-diarization-test \
  bash scripts/start_voice_job.sh

# Or test with command args
docker run --rm \
  -e SUPABASE_URL="$SUPABASE_URL" \
  -e SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" \
  -e GOOGLE_DRIVE_CREDENTIALS="$GOOGLE_DRIVE_CREDENTIALS" \
  -e AAI_API_KEY="$AAI_API_KEY" \
  voice-diarization-test \
  bash scripts/start_voice_job.sh c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06
```

**Expected**:
- ✓ Compatibility tests pass
- ✓ Database connection succeeds
- ✓ Google Drive authentication works
- Job will fail at GPU step (expected without GPU)

### B. Test Import Diagnostics

```bash
docker run --rm voice-diarization-test python scripts/test_pydantic_imports.py
```

**Expected output**:
```
✓ Pydantic version: 2.x.x
✓ Realtime Import: ✓
✓ Supabase Import: ✓
✓ Lightweight DB Module: ✓
```

### C. Test Database Connection

```bash
docker run --rm \
  -e SUPABASE_URL="$SUPABASE_URL" \
  -e SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" \
  voice-diarization-test \
  python -c "from services.database_voice import SupaVoice; db = SupaVoice(); workers = db.get_workers(); print(f'Found {len(workers)} workers')"
```

**Expected**: Should print the number of workers in your database.

---

## Method 4: Test Individual Components

### Test Voice Diarization Service

```bash
cd backend

# Test imports only
python -c "from services.voice_diarization import VoiceDiarization; print('✓ Voice service imports')"

# Test initialization (without GPU)
python -c "
import os
os.environ['SUPABASE_URL'] = 'https://your-project.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'your-key'
os.environ['AAI_API_KEY'] = 'your-key'

from services.voice_diarization import VoiceDiarization
vd = VoiceDiarization()
print('✓ Voice service initialized')
"
```

### Test Pipeline

```bash
python -c "from pipeline.voice_diarization_pipeline import voice_diarization_pipeline; print('✓ Pipeline imports')"
```

### Test Monitoring

```bash
python -c "from services.monitoring import MonitoringService; m = MonitoringService(); print(m.get_health_status())"
```

---

## Quick Test Checklist

Before deploying, verify:

- [ ] `python scripts/test_pydantic_imports.py` - All checks pass
- [ ] Docker image builds without errors
- [ ] Container starts and runs compatibility tests
- [ ] Database connection works (if credentials provided)
- [ ] Import errors are resolved

---

## Common Issues & Fixes

### Issue: "ImportError: cannot import name 'with_config'"

**Test**:
```bash
docker run --rm voice-diarization-test python scripts/fix_pydantic_compat.py --test
```

**Expected**: Should show compatibility patch applied successfully.

### Issue: "No module named 'services.database'"

**Test**:
```bash
docker run --rm voice-diarization-test python -c "from services.database_voice import SupaVoice; print('Fallback works')"
```

**Expected**: Should import without errors.

### Issue: Docker build fails

**Check**:
```bash
# Check if you're in the right directory (repo root, not backend/)
pwd  # Should be: /Users/aarav/Desktop/Aarav/Miscellaneous/Projects/hoptix

# Check Dockerfile exists
ls backend/Dockerfile.gpu-pytorch-base
```

---

## Testing Without Full Environment

If you don't have all the API keys/credentials, you can still test imports:

```bash
# Test with minimal env vars
docker run --rm \
  -e SUPABASE_URL="https://dummy.supabase.co" \
  -e SUPABASE_SERVICE_KEY="dummy-key" \
  -e AAI_API_KEY="dummy-key" \
  voice-diarization-test \
  python scripts/test_pydantic_imports.py
```

This will test that all the imports work correctly, even if connections fail later.

---

## Summary

**For fastest feedback** (30 seconds):
```bash
cd backend
python scripts/test_pydantic_imports.py
```

**For complete testing** (10 minutes):
```bash
cd /Users/aarav/Desktop/Aarav/Miscellaneous/Projects/hoptix
docker build -f backend/Dockerfile.gpu-pytorch-base -t voice-diarization-test .
docker run --rm voice-diarization-test python scripts/test_pydantic_imports.py
```

**For production simulation** (15 minutes):
```bash
# Set all your env vars first, then:
docker run --rm \
  -e SUPABASE_URL="$SUPABASE_URL" \
  -e SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" \
  -e GOOGLE_DRIVE_CREDENTIALS="$GOOGLE_DRIVE_CREDENTIALS" \
  -e AAI_API_KEY="$AAI_API_KEY" \
  -e LOCATION_ID="your-location-id" \
  -e DATE="2025-10-06" \
  voice-diarization-test \
  bash scripts/start_voice_job.sh
```