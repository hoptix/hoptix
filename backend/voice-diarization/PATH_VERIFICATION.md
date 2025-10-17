# Path Verification for Voice Diarization Deployment

## ✅ All Paths Are Correct

This document verifies all paths in the voice diarization deployment are properly configured.

### Porter Configuration (`backend/porter.yaml`)

```yaml
build:
  context: ./              # Build context is repository root
  dockerfile: ./backend/voice-diarization/Dockerfile
```

**✅ Correct:** Dockerfile path is relative to repo root

### Dockerfile COPY Commands

Since build context is `./` (repo root), all COPY commands must use `backend/voice-diarization/` prefix:

**Line 32 - Requirements files:**
```dockerfile
COPY backend/voice-diarization/requirements-voice-core.txt \
     backend/voice-diarization/requirements-voice-nemo.txt /tmp/
```
✅ **Correct:** Paths include `backend/voice-diarization/` prefix

**Lines 106-108 - Application code:**
```dockerfile
COPY --chown=voiceuser:voiceuser backend/voice-diarization/voice_job.py \
     backend/voice-diarization/health_check.py /app/
COPY --chown=voiceuser:voiceuser backend/voice-diarization/services/ /app/services/
COPY --chown=voiceuser:voiceuser backend/voice-diarization/pipeline/ /app/pipeline/
```
✅ **Correct:** All paths include `backend/voice-diarization/` prefix

### File Structure

```
repository-root/           # Build context starts here
└── backend/
    └── voice-diarization/
        ├── Dockerfile     # Referenced by porter.yaml
        ├── requirements-voice-core.txt
        ├── requirements-voice-nemo.txt
        ├── voice_job.py
        ├── health_check.py
        ├── services/
        │   ├── __init__.py
        │   ├── database_rest.py
        │   └── gdrive_client.py
        └── pipeline/
            ├── __init__.py
            └── voice_diarization_pipeline.py
```

### Runtime Paths

Once built, the container has:
```
/app/
├── voice_job.py           # Main entry point
├── health_check.py        # Health monitoring
├── services/
│   ├── database_rest.py
│   └── gdrive_client.py
└── pipeline/
    └── voice_diarization_pipeline.py
```

**Command:** `python -u voice_job.py`
✅ **Correct:** Runs from `/app` working directory

### Environment Variables

Set in Porter dashboard (no path changes needed):
- `PYTHONPATH=/app` - Pre-configured in porter.yaml
- All other env vars are URLs/keys, not paths

## Verification Checklist

- [x] Build context set to repository root
- [x] Dockerfile path correct in porter.yaml
- [x] All COPY commands use `backend/voice-diarization/` prefix
- [x] Requirements files in correct location
- [x] Application files in correct location
- [x] Run command matches Dockerfile CMD
- [x] Working directory is `/app`
- [x] PYTHONPATH is set correctly

## If Build Fails

1. **Clear Porter cache:** In Porter dashboard, trigger a fresh build (no cache)
2. **Verify paths:** All paths should match this document exactly
3. **Check git:** Ensure latest commit is deployed (`9062efc` or newer)

## Version History

- **v2.0.1** - Fixed all paths with cache-busting commit (current)
- **v2.0.0** - Initial refactor
- **v1.x.x** - Legacy (deprecated)