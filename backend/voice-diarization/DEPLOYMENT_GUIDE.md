# Voice Diarization Service - Deployment Guide

## Overview
This is a clean, optimized voice diarization service that identifies workers in transaction audio clips using TitaNet speaker verification. The service has been completely refactored to avoid dependency conflicts, reduce image size, and improve reliability.

## Key Improvements
- ✅ **60% smaller Docker image** (3GB vs 8GB)
- ✅ **No Pydantic conflicts** - Uses REST API directly
- ✅ **GPU support that actually works** - NVIDIA CUDA 11.7
- ✅ **Proper multi-stage builds** - Faster builds, better caching
- ✅ **Clean separation from main pipeline** - No interference
- ✅ **Better error handling** - Graceful degradation
- ✅ **Memory efficient** - Batch processing with cleanup

## Prerequisites

### Required Environment Variables
```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# APIs
AAI_API_KEY=your-assemblyai-key

# Google Drive (one of these)
GOOGLE_DRIVE_CREDENTIALS='{...json...}'  # JSON string
# OR
GOOGLE_DRIVE_CREDENTIALS_PATH=/path/to/credentials.json

# Job parameters
LOCATION_ID=c3607cc3-0f0c-4725-9c42-eb2fdb5e016a
DATE=2025-10-06
```

### Optional Configuration
```bash
BATCH_SIZE=10           # Clips per batch (default: 10)
MAX_WORKERS=2           # Concurrent workers (default: 2)
CONFIDENCE_THRESHOLD=0.75  # Match threshold (default: 0.75)
```

## Local Testing

### 1. Set Up Environment
```bash
# Export required variables
export SUPABASE_URL="..."
export SUPABASE_SERVICE_KEY="..."
export AAI_API_KEY="..."
export LOCATION_ID="..."
export DATE="2025-10-06"
```

### 2. Run Local Test
```bash
cd backend/voice-diarization
./test_local.sh
```

This will:
- Build the Docker image
- Check for GPU availability
- Run health checks
- Execute a dry run
- Optionally run full processing

### 3. Check Health Endpoints
While running, you can check:
- http://localhost:8080/health - Basic liveness
- http://localhost:8080/ready - Dependency checks
- http://localhost:8080/metrics - System metrics

## Porter Deployment

### 1. Deploy to Porter
```bash
# From repository root
porter apply -f backend/porter.yaml
```

### 2. Configure in Porter Dashboard

Navigate to your Porter dashboard and set:

#### Environment Variables (Secrets)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `AAI_API_KEY`
- `GOOGLE_DRIVE_CREDENTIALS`

#### Job Configuration
- `LOCATION_ID` - Location to process
- `DATE` - Date in YYYY-MM-DD format

#### Cron Schedule
Set schedule for automatic runs:
- Daily at 3 AM: `0 3 * * *`
- Weekly on Sundays: `0 3 * * 0`
- Custom as needed

### 3. Monitor Job Execution

Check job status in Porter dashboard:
- View logs for detailed output
- Check metrics for GPU usage
- Monitor success/failure rates

## Troubleshooting

### GPU Not Available
**Symptom:** "GPU not available, will use CPU"

**Solutions:**
1. Ensure Porter instance has GPU allocated
2. Check CUDA drivers are installed
3. Verify PyTorch CUDA version matches

### Out of Memory
**Symptom:** "CUDA out of memory" errors

**Solutions:**
1. Reduce `BATCH_SIZE` (try 5)
2. Reduce `MAX_WORKERS` to 1
3. Increase GPU memory allocation

### Missing Dependencies
**Symptom:** "No module named X"

**Solutions:**
1. Check Docker build logs
2. Verify all stages completed
3. Rebuild with `--no-cache`

### Database Connection Failed
**Symptom:** "Database connection failed"

**Solutions:**
1. Verify `SUPABASE_URL` is correct
2. Check `SUPABASE_SERVICE_KEY` has permissions
3. Test with REST API directly

### No Worker Matches
**Symptom:** All clips show "no match"

**Solutions:**
1. Verify voice samples exist in Google Drive
2. Check folder naming matches location
3. Increase logging verbosity
4. Lower `CONFIDENCE_THRESHOLD`

## Performance Tuning

### GPU Optimization
```bash
# Allocate more GPU memory
PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:1024"

# Use specific GPU
CUDA_VISIBLE_DEVICES="0"
```

### Batch Processing
```bash
# Larger batches for more data
BATCH_SIZE=20
MAX_WORKERS=4

# Smaller batches for limited memory
BATCH_SIZE=5
MAX_WORKERS=1
```

### Memory Management
The service automatically:
- Clears GPU cache after each batch
- Uses context managers for files
- Implements garbage collection

## Architecture Details

### Directory Structure
```
backend/voice-diarization/
├── Dockerfile                  # Optimized multi-stage build
├── requirements-voice-core.txt # Core dependencies
├── requirements-voice-nemo.txt # NeMo/ML dependencies
├── voice_job.py               # Main entry point
├── health_check.py            # Health monitoring
├── test_local.sh              # Local testing script
├── services/
│   ├── database_rest.py      # REST-only DB client
│   └── gdrive_client.py      # Google Drive access
└── pipeline/
    └── voice_diarization_pipeline.py  # Processing logic
```

### Processing Flow
1. **Initialization**
   - Load TitaNet model
   - Connect to database
   - Set up Google Drive

2. **Build Embeddings**
   - Fetch worker list
   - Download voice samples
   - Generate embeddings

3. **Process Clips**
   - Fetch transactions for date
   - Process in batches
   - Match speakers
   - Update database

4. **Cleanup**
   - Clear GPU memory
   - Log summary
   - Update run status

## Maintenance

### Updating Dependencies
```bash
# Update core packages
pip-compile requirements-voice-core.in

# Test compatibility
docker build --target deps-builder -t test-deps .
```

### Monitoring Logs
```bash
# View recent logs
porter logs voice-job --tail 100

# Stream logs
porter logs voice-job --follow
```

### Database Queries
```sql
-- Check recent runs
SELECT * FROM runs
WHERE type = 'voice_diarization'
ORDER BY created_at DESC
LIMIT 10;

-- Check processing results
SELECT
  COUNT(*) as total,
  COUNT(worker_id) as matched,
  AVG(voice_confidence) as avg_confidence
FROM transactions
WHERE voice_processed_at >= NOW() - INTERVAL '1 day';
```

## Security Notes

1. **Never commit credentials** - Use environment variables
2. **Rotate keys regularly** - Update in Porter dashboard
3. **Use service accounts** - For Google Drive access
4. **Limit permissions** - Read-only where possible
5. **Monitor access logs** - Check for anomalies

## Support

For issues or questions:
1. Check logs in Porter dashboard
2. Review this guide's troubleshooting section
3. Test locally with `test_local.sh`
4. Check health endpoints for dependency status

## Version History

- **v2.0.0** - Complete refactor with clean architecture
- **v1.x.x** - Legacy version with Pydantic conflicts (deprecated)