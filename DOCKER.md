# Docker Deployment Guide

This guide explains how to build and deploy the Hoptix application using Docker and Docker Compose.

## Architecture

The Hoptix application consists of three services:

1. **Auth Service** (Go) - Port 8081
   - JWT authentication and authorization
   - User management via Supabase Auth

2. **Backend** (Flask/Python) - Port 8000
   - Analytics API
   - Transaction processing
   - Audio transcription and grading

3. **Frontend** (Next.js 15) - Port 3000
   - React dashboard
   - Data visualization
   - User interface

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd hoptix
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

**Required Variables:**
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SUPABASE_SERVICE_KEY` - Supabase service role key (backend only)
- `AWS_ACCESS_KEY_ID` - AWS access key for S3
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `RAW_BUCKET` - S3 bucket name for raw audio files
- `OPENAI_API_KEY` - OpenAI API key for transcription

See `.env.example` for complete list and descriptions.

### 3. Build and Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f auth-service
docker-compose logs -f frontend
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Auth Service**: http://localhost:8081

## Service Details

### Auth Service

**Dockerfile**: `auth-service/Dockerfile`
- Base: `golang:1.24.3` (builder), `debian:12-slim` (runtime)
- Port: 8081
- Health check: `curl http://localhost:8081/health`

**Build standalone:**
```bash
cd auth-service
docker build -t hoptix-auth-service .
docker run -p 8081:8081 \
  -e SUPABASE_URL=your-url \
  -e SUPABASE_ANON_KEY=your-key \
  -e PORT=8081 \
  hoptix-auth-service
```

### Backend

**Dockerfile**: `backend/Dockerfile`
- Base: `python:3.11.12-slim`
- Port: 8000
- Health check: `curl http://localhost:8000/health`

**Build standalone:**
```bash
cd backend
docker build -t hoptix-backend .
docker run -p 8000:8000 \
  -e SUPABASE_URL=your-url \
  -e SUPABASE_SERVICE_KEY=your-key \
  -e AUTH_SERVICE_URL=http://auth-service:8081 \
  -e OPENAI_API_KEY=your-key \
  hoptix-backend
```

### Frontend

**Dockerfile**: `frontend/Dockerfile`
- Base: `node:18-alpine`
- Port: 3000
- Output: Next.js standalone build

**Build standalone:**
```bash
cd frontend
docker build -t hoptix-frontend \
  --build-arg NEXT_PUBLIC_SUPABASE_URL=your-url \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=your-key \
  --build-arg NEXT_PUBLIC_FLASK_API_URL=http://localhost:8000 \
  --build-arg NEXT_PUBLIC_AUTH_SERVICE_URL=http://localhost:8081 \
  .
docker run -p 3000:3000 hoptix-frontend
```

## Docker Compose Commands

```bash
# Start services in detached mode
docker-compose up -d

# Stop services
docker-compose down

# Rebuild and start (after code changes)
docker-compose up -d --build

# View status
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# Restart specific service
docker-compose restart backend

# Stop specific service
docker-compose stop frontend

# Remove containers and volumes
docker-compose down -v

# Execute command in running container
docker-compose exec backend bash
docker-compose exec frontend sh
```

## Troubleshooting

### Port Conflicts

If ports 3000, 8000, or 8081 are already in use:

1. Edit `docker-compose.yml` and change port mappings:
   ```yaml
   ports:
     - "3001:3000"  # Use 3001 on host instead of 3000
   ```

2. Update frontend environment variables if backend/auth ports change

### Container Fails to Start

Check logs:
```bash
docker-compose logs backend
```

Common issues:
- Missing environment variables (check `.env` file)
- Database connection failed (verify Supabase credentials)
- Port already in use (check with `lsof -i :8000`)

### Frontend Build Issues

If frontend build fails with memory errors:

```bash
# Increase Docker memory limit in Docker Desktop settings
# Then rebuild:
docker-compose build --no-cache frontend
```

### Backend Dependencies

If backend fails to install dependencies:

```bash
# Rebuild with no cache
docker-compose build --no-cache backend
```

## Production Deployment

### Security Considerations

1. **Use secrets management** - Don't commit `.env` file
2. **Use HTTPS** - Configure reverse proxy (nginx/traefik)
3. **Restrict CORS** - Update backend CORS settings for production
4. **Use production database** - Separate from development
5. **Enable rate limiting** - Protect APIs from abuse

### Recommended Setup

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  auth-service:
    image: hoptix-auth-service:latest
    restart: always
    # ... configuration

  backend:
    image: hoptix-backend:latest
    restart: always
    # ... configuration

  frontend:
    image: hoptix-frontend:latest
    restart: always
    # ... configuration

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
      - auth-service
```

### Environment-Specific Configs

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Monitoring

### Health Checks

All services include health checks:

```bash
# Check health status
docker-compose ps

# Manually test endpoints
curl http://localhost:8000/health  # Backend
curl http://localhost:8081/health  # Auth service
curl http://localhost:3000          # Frontend
```

### Logs

```bash
# Real-time logs from all services
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific time range
docker-compose logs --since 2024-10-01T10:00:00
```

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Complete cleanup
docker system prune -a --volumes
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Next.js Docker Documentation](https://nextjs.org/docs/deployment#docker-image)
- [Flask Docker Guide](https://flask.palletsprojects.com/en/latest/tutorial/deploy/)
