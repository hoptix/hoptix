# Hoptix Flask Server - Docker Deployment Guide

This guide explains how to run the Hoptix Flask server using Docker and Docker Compose.

## Quick Start

### 1. Environment Setup
```bash
# Copy the environment template
cp env.template .env

# Edit .env with your actual values
nano .env
```

### 2. Build and Run with Docker Compose
```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f hoptix-flask
docker-compose logs -f hoptix-worker
```

### 3. Test the Application
```bash
# Health check
curl http://localhost:8000/health

# Onboard a restaurant
curl -X POST http://localhost:8000/onboard-restaurant \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_name": "Test Restaurant",
    "location_name": "Main Location",
    "timezone": "America/New_York"
  }'
```

## Docker Services

### hoptix-flask
- **Purpose**: Main Flask web server
- **Port**: 8000
- **Health Check**: `/health` endpoint
- **Auto-restart**: Yes

### hoptix-worker (Optional)
- **Purpose**: SQS video processing workers
- **Replicas**: 2 (configurable)
- **Auto-restart**: Yes

## Environment Variables

Required environment variables (see `env.template`):

### Database
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_KEY`: Supabase service role key

### AWS
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_REGION`: AWS region (default: us-east-1)
- `RAW_BUCKET`: S3 bucket for raw videos
- `DERIV_BUCKET`: S3 bucket for processed data

### SQS (for workers)
- `SQS_QUEUE_URL`: SQS queue URL for video processing
- `SQS_DLQ_URL`: Dead letter queue URL

### OpenAI
- `OPENAI_API_KEY`: OpenAI API key for transcription

## Volume Mounts

- `./logs:/app/logs` - Persistent logs
- `./exports:/app/exports` - CSV exports
- `./token.json:/app/token.json` - Google Drive API token (read-only)
- `./prompts:/app/prompts` - Menu prompts (read-only)

## Docker Commands

### Build Only
```bash
docker build -t hoptix-flask .
```

### Run Flask Server Only
```bash
docker run -d \
  --name hoptix-flask \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/exports:/app/exports \
  -v $(pwd)/token.json:/app/token.json:ro \
  -v $(pwd)/prompts:/app/prompts:ro \
  hoptix-flask
```

### Run Worker Only
```bash
docker run -d \
  --name hoptix-worker \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/exports:/app/exports \
  -v $(pwd)/token.json:/app/token.json:ro \
  -v $(pwd)/prompts:/app/prompts:ro \
  hoptix-flask \
  python -m worker.sqs_worker
```

## Scaling Workers

Scale the number of SQS workers:
```bash
docker-compose up -d --scale hoptix-worker=5
```

## Monitoring

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f hoptix-flask
docker-compose logs -f hoptix-worker

# Last 100 lines
docker-compose logs --tail=100 hoptix-flask
```

### Container Status
```bash
docker-compose ps
```

### Resource Usage
```bash
docker stats
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Change port in docker-compose.yml
   ports:
     - "8001:8000"  # Use port 8001 instead
   ```

2. **Permission errors with volumes**
   ```bash
   # Fix permissions
   sudo chown -R $USER:$USER logs exports
   chmod -R 755 logs exports
   ```

3. **Environment variables not loaded**
   ```bash
   # Verify .env file exists and has correct values
   cat .env
   
   # Rebuild containers
   docker-compose down
   docker-compose up --build
   ```

4. **Audio processing errors**
   - The Docker image includes ffmpeg and audio libraries
   - Check container logs for specific audio errors
   - Ensure video files are not corrupted

### Debug Container
```bash
# Run interactive shell in container
docker-compose exec hoptix-flask bash

# Or start a new container for debugging
docker run -it --rm \
  --env-file .env \
  -v $(pwd):/app \
  hoptix-flask bash
```

## Production Deployment

### Security Considerations
1. Use Docker secrets for sensitive environment variables
2. Run containers as non-root user (already configured)
3. Use proper firewall rules
4. Enable TLS/SSL with a reverse proxy

### Performance Tuning
1. Adjust Gunicorn workers based on CPU cores
2. Configure proper memory limits
3. Use external volumes for persistent data
4. Monitor resource usage

### Example Production docker-compose.yml
```yaml
version: '3.8'

services:
  hoptix-flask:
    image: your-registry/hoptix-flask:latest
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
    environment:
      - FLASK_ENV=production
    secrets:
      - supabase_key
      - aws_secret_key
      - openai_api_key

secrets:
  supabase_key:
    external: true
  aws_secret_key:
    external: true
  openai_api_key:
    external: true
```

## Backup and Recovery

### Backup Important Data
```bash
# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Backup exports
tar -czf exports-backup-$(date +%Y%m%d).tar.gz exports/

# Backup configuration
cp .env env-backup-$(date +%Y%m%d)
```

### Container Updates
```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d

# Clean up old images
docker image prune
```

