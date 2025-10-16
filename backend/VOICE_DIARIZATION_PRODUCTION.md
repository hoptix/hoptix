# Voice Diarization Production Enhancements

## Overview

The voice diarization system has been enhanced with comprehensive production-ready features including error handling, monitoring, health checks, and retry logic. This document describes the enhancements and how to use them.

## Key Enhancements

### 1. Comprehensive Error Handling

- **Bug Fix**: Empty Supabase query results are now properly handled (services/voice_diarization.py:136)
- **Graceful Degradation**: Missing files, API failures, and GPU issues are caught and logged
- **Transaction Safety**: Each transaction is checked for completion status before processing
- **Cleanup**: Temporary files are cleaned up even on failure using try/finally blocks

### 2. Retry Logic for External Services

All external service calls now have automatic retry with exponential backoff:

- **AssemblyAI Transcription**: 3 retries with 5s, 10s, 15s backoff (line 261-291)
- **Supabase Operations**: 2-3 retries with exponential backoff
  - Worker fetching: @retry_with_monitoring decorator
  - Transaction checking: @retry_with_monitoring decorator
- **Google Drive Operations**: 3 retries for all operations
  - Folder ID lookup: _get_gdrive_folder_id()
  - File listing: _list_gdrive_files()
  - File download: _download_gdrive_file()

### 3. Monitoring and Alerting System

**MonitoringService** (services/monitoring.py):
- Tracks job starts, completions, and failures
- Records API call metrics (success/failure rates)
- Memory usage monitoring
- Performance threshold alerts
- Webhook integrations (Slack, Discord, generic)

**Metrics Tracked**:
- Job completion rates
- Transaction processing statistics
- API call performance
- Memory usage
- Error frequency

**Alert Channels**:
Configure via environment variables:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export MONITORING_WEBHOOK_URL="https://your-webhook.com/alerts"
```

### 4. Health Check Endpoints

**HTTP Health Check Server** (scripts/health_check.py):

Three endpoints for monitoring:

1. **/health** - Overall system health
   ```json
   {
     "status": "healthy|unhealthy",
     "issues": [],
     "metrics": {...},
     "timestamp": "2025-10-16T..."
   }
   ```

2. **/ready** - Readiness probe
   ```json
   {
     "ready": true,
     "checks": {
       "database": true,
       "google_drive": true,
       "assemblyai": true,
       "gpu": true
     }
   }
   ```

3. **/metrics** - Prometheus-compatible metrics
   ```
   # HELP voice_diarization_jobs_total Total number of jobs started
   # TYPE voice_diarization_jobs_total counter
   voice_diarization_jobs_total 42
   ```

### 5. Validation Script

**Pre-flight Validation** (scripts/validate_voice_setup.py):
Checks before running:
- Environment variables
- Python dependencies
- GPU availability
- Google Drive access
- Database connectivity
- AssemblyAI API key

Run validation:
```bash
python scripts/validate_voice_setup.py
```

### 6. Safe Wrapper Script

**Production Wrapper** (scripts/run_voice_diarization_safe.sh):
- Runs validation before processing
- Adds 6-hour timeout protection
- Proper exit codes for monitoring
- Clear error messages

## Configuration

### Environment Variables

Required:
```bash
# API Keys
AAI_API_KEY="your-assemblyai-key"

# Database
SUPABASE_URL="https://xxx.supabase.co"
SUPABASE_SERVICE_KEY="your-service-key"

# Google Drive
GOOGLE_DRIVE_CREDENTIALS='{"type": "service_account", ...}'
VOICE_SAMPLES_FOLDER="Cary Voice Samples"
VOICE_CLIPS_FOLDER="Clips_2025-10-06_0700"
```

Optional:
```bash
# Performance
VOICE_DIARIZATION_THRESHOLD="0.2"  # Cosine similarity threshold
VOICE_PARALLEL_WORKERS="5"          # Concurrent clip processing
VOICE_MIN_UTTERANCE_MS="1000"       # Minimum utterance length

# Monitoring
MAX_JOB_DURATION="21600"           # 6 hours in seconds
MAX_MEMORY_GB="7.5"                # Memory threshold
MIN_SUCCESS_RATE="0.7"             # Minimum match rate
MAX_API_FAILURES="10"              # API failure threshold

# Alerting
SLACK_WEBHOOK_URL="..."
DISCORD_WEBHOOK_URL="..."
NOTIFY_JOB_START="true"            # Notify on job start
```

## Usage

### Basic Usage

Single date processing:
```bash
python scripts/run_voice_diarization.py c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06
```

### With Health Check Server

Enable health monitoring:
```bash
python scripts/run_voice_diarization.py \
  c3607cc3-0f0c-4725-9c42-eb2fdb5e016a \
  2025-10-06 \
  --enable-health-check \
  --health-check-port 8080
```

### Production Deployment (Porter)

1. **Docker Command**:
```bash
docker run -p 8080:8080 voice-diarization:latest \
  python scripts/run_voice_diarization.py \
  $LOCATION_ID $DATE \
  --enable-health-check
```

2. **Porter Configuration**:
```yaml
services:
  - name: voice-diarization-job
    type: job
    run: python scripts/run_voice_diarization.py $LOCATION_ID $DATE --enable-health-check
    cpuCores: 2
    ramMegabytes: 8192
    gpuCoresNvidia: 1
    health:
      path: /health
      port: 8080
      interval: 30s
      timeout: 10s
```

### Safe Production Run

Using the wrapper script:
```bash
./scripts/run_voice_diarization_safe.sh c3607cc3-0f0c-4725-9c42-eb2fdb5e016a 2025-10-06
```

### Validation Only

Check setup without processing:
```bash
python scripts/validate_voice_setup.py
```

### Dry Run

Preview without processing:
```bash
python scripts/run_voice_diarization.py \
  c3607cc3-0f0c-4725-9c42-eb2fdb5e016a \
  2025-10-06 \
  --dry-run
```

## Monitoring Best Practices

1. **Set up alerting webhooks** for critical failures
2. **Monitor the /health endpoint** every 30-60 seconds
3. **Track metrics** in your monitoring system (Prometheus, Datadog, etc.)
4. **Review logs** for retry attempts and API failures
5. **Set memory thresholds** based on your GPU capacity
6. **Configure job timeouts** based on typical processing times

## Troubleshooting

### Common Issues

1. **GPU Memory Errors**:
   - Reduce VOICE_PARALLEL_WORKERS
   - Check memory with monitoring endpoint
   - Restart to clear GPU memory

2. **API Rate Limits**:
   - Retry logic will handle temporary failures
   - Check metrics endpoint for failure rates
   - Reduce parallel processing if needed

3. **Google Drive Access**:
   - Run validation script
   - Check folder permissions
   - Verify credentials JSON

4. **Database Connectivity**:
   - Check SUPABASE_URL and SUPABASE_SERVICE_KEY
   - Verify network connectivity
   - Check Supabase service status

### Debug Mode

Enable verbose logging:
```bash
python scripts/run_voice_diarization.py \
  c3607cc3-0f0c-4725-9c42-eb2fdb5e016a \
  2025-10-06 \
  --verbose
```

### Health Check CLI

One-time health check:
```bash
python scripts/health_check.py --once
```

## Performance Optimization

1. **Parallel Processing**: Adjust VOICE_PARALLEL_WORKERS based on GPU memory
2. **Batch Size**: Process multiple dates with date range feature
3. **Caching**: Voice embeddings are cached during batch processing
4. **Memory Management**: Automatic garbage collection after processing
5. **GPU Optimization**: TitaNet model loaded once and reused

## Security Notes

- All credentials stored as environment variables
- Service keys never logged
- Webhook URLs support HTTPS only
- Temporary files cleaned up automatically
- No sensitive data in health endpoints