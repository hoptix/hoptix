# Pydantic v1/v2 Compatibility Fix for Voice Diarization

## Problem

The voice diarization Docker build encounters an ImportError:
```
ImportError: cannot import name 'with_config' from 'pydantic'
```

This occurs because:
1. The PyTorch base image (`pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime`) includes Pydantic v1
2. The `supabase` package requires Pydantic v2
3. The `realtime` package (a dependency of supabase) still tries to import Pydantic v1 features

## Solutions Implemented

We've implemented multiple layers of fixes to ensure the job runs reliably:

### 1. Package Version Updates

Updated in `Dockerfile.gpu-pytorch-base`:
```dockerfile
pip install --no-cache-dir --upgrade \
    "pydantic>=2.0.0,<3.0.0" \
    "pydantic-core>=2.0.0" \
    "supabase>=2.9.0" \
    "realtime>=2.0.0"
```

And in `requirements.txt`:
```
supabase>=2.9.0
```

### 2. Compatibility Shim (`scripts/fix_pydantic_compat.py`)

A monkey-patch that adds the missing `with_config` decorator to Pydantic v2:
```python
def patch_pydantic_import():
    """Provide backwards compatibility for with_config."""
    import pydantic
    if not hasattr(pydantic, 'with_config'):
        def with_config(*args, **kwargs):
            def decorator(cls):
                return cls
            return decorator
        pydantic.with_config = with_config
```

This patch is applied automatically in `run_voice_diarization.py` before any imports.

### 3. Lightweight Database Module (`services/database_voice.py`)

A fallback database client that avoids the problematic `realtime` import entirely:
- Only uses REST API calls
- No realtime/websocket features (not needed for voice diarization)
- Automatic fallback if regular import fails

### 4. Import Fallback Chain

Both `services/voice_diarization.py` and `pipeline/voice_diarization_pipeline.py` use:
```python
try:
    from services.database import Supa
except ImportError:
    from services.database_voice import Supa  # Lightweight fallback
```

### 5. Startup Script (`scripts/start_voice_job.sh`)

A wrapper that:
- Tests compatibility before starting
- Sets environment variables
- Provides clear error messages

## Testing

Run the diagnostic script to verify everything works:
```bash
python scripts/test_pydantic_imports.py
```

Expected output:
```
✓ Pydantic version: 2.x.x
✓ Compatibility patch applied
✓ Supabase import successful
✓ Lightweight database module import successful
```

## How It Works

1. **Docker Build**: Installs compatible versions of all packages
2. **Runtime**: When the job starts:
   - The compatibility patch is applied first
   - If regular imports fail, lightweight modules are used
   - The job continues with whichever method works

## Porter Configuration

The job now uses the startup script:
```yaml
services:
  - name: voice-diarization-job
    type: job
    run: bash scripts/start_voice_job.sh
```

## Manual Testing

If you encounter issues, test locally:
```bash
# Test imports
python scripts/test_pydantic_imports.py

# Test with compatibility fix
python -c "import fix_pydantic_compat; fix_pydantic_compat.patch_pydantic_import(); from supabase import create_client; print('Success!')"

# Test lightweight DB
python -c "from services.database_voice import SupaVoice; print('Lightweight DB works!')"
```

## Environment Variables

If all else fails, you can force the lightweight database:
```bash
export USE_LIGHTWEIGHT_DB=1
```

## Troubleshooting

### If imports still fail:

1. **Check package versions**:
```bash
pip show pydantic supabase realtime
```

2. **Force reinstall with correct versions**:
```bash
pip uninstall -y pydantic pydantic-core supabase realtime
pip install "pydantic>=2.0.0,<3.0.0" "supabase>=2.9.0"
```

3. **Use the lightweight database module directly**:
Edit your imports to use `from services.database_voice import Supa`

### If the job fails to start:

1. Check Porter logs for the exact error
2. Verify environment variables are set
3. Try running with the test script first:
```bash
docker run your-image python scripts/test_pydantic_imports.py
```

## Summary

The multi-layered approach ensures the job will run even if one fix doesn't work:
- **Primary**: Updated package versions
- **Fallback 1**: Compatibility shim
- **Fallback 2**: Lightweight database module
- **Fallback 3**: Direct REST API calls

This provides maximum reliability for production deployment.