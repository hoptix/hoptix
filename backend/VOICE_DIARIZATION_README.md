# Voice Diarization System

## Overview

Voice diarization system that identifies workers by their voice using TitaNet embeddings and AssemblyAI transcription.

## Files

### Core Services
- `services/voice_diarization.py` - Main voice processing service with TitaNet
- `services/monitoring.py` - Monitoring and alerting system
- `services/database_voice.py` - Lightweight database module (fallback)
- `pipeline/voice_diarization_pipeline.py` - Main orchestration

### Scripts
- `scripts/run_voice_diarization.py` - Main CLI script
- `scripts/start_voice_job.sh` - Docker entrypoint script
- `scripts/run_voice_today.sh` - Convenience script for daily runs
- `scripts/run_voice_diarization_safe.sh` - Wrapper with validation
- `scripts/validate_voice_setup.py` - Pre-flight validation
- `scripts/health_check.py` - Health check HTTP server

### Configuration
- `porter.yaml` - Porter deployment configuration
- `Dockerfile.porter-only` - Docker image for Porter deployment
- `requirements-voice-minimal.txt` - Voice-specific Python dependencies

## Environment Variables

Required:
```bash
# API Keys
AAI_API_KEY=your-assemblyai-key
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
GOOGLE_DRIVE_CREDENTIALS='{"type": "service_account", ...}'

# Voice Configuration
VOICE_SAMPLES_FOLDER="Cary Voice Samples"
VOICE_CLIPS_FOLDER="Clips_2025-10-06_0700"  # Optional, auto-generated

# Job Parameters (for CRON)
LOCATION_ID=c3607cc3-0f0c-4725-9c42-eb2fdb5e016a
DATE=2025-10-06  # Or pass via command args
```

## Usage

### Manual Run
```bash
python scripts/run_voice_diarization.py <location_id> <date>
```

### Daily Run (uses today's date)
```bash
bash scripts/run_voice_today.sh <location_id>
```

### With Health Monitoring
```bash
python scripts/run_voice_diarization.py <location_id> <date> --enable-health-check
```

### Validation Only
```bash
python scripts/validate_voice_setup.py
```

## Porter Deployment

The system deploys via Porter using `porter.yaml` which references `Dockerfile.porter-only`.

### Deploy
```bash
git add .
git commit -m "Deploy voice diarization"
git push
```

### Configure in Porter Dashboard
1. Set environment variables (see above)
2. Configure CRON schedule
3. Set GPU allocation (1 GPU required)

## Architecture

1. **Voice Samples**: Reference voice samples stored in Google Drive
2. **Transaction Clips**: Audio clips to be processed
3. **TitaNet Model**: NVIDIA's speaker verification model (192-dim embeddings)
4. **AssemblyAI**: Transcription with speaker diarization
5. **Database**: Worker assignments stored in Supabase

## Monitoring

- Health check endpoint: `/health` (port 8080)
- Metrics endpoint: `/metrics` (Prometheus format)
- Alerts via Slack/Discord webhooks (optional)

## Troubleshooting

### Import Errors
The Docker image installs Pydantic v2 first to avoid conflicts with supabase dependencies.

### GPU Memory
Adjust `VOICE_PARALLEL_WORKERS` environment variable if running out of GPU memory.

### API Rate Limits
The system includes retry logic with exponential backoff for all external APIs.