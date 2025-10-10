# Backend Deployment Guide

## Overview
This guide covers deploying the Hoptix backend to Porter with production-ready configuration.

## ✅ Fixed Issues

### Issue #1: 502 Bad Gateway (RESOLVED)
**Problem:** Flask was binding to `127.0.0.1` (localhost only), making it unreachable from outside the container.

**Solution:** Updated `app.py` to bind to `0.0.0.0` (all interfaces).

### Issue #2: Development Server in Production (RESOLVED)
**Problem:** Using Flask's built-in development server in production.

**Solution:** Switched to Gunicorn, a production-grade WSGI server.

### Issue #3: Missing Dockerfile CMD (RESOLVED)
**Problem:** Dockerfile had no CMD, relying on external configuration.

**Solution:** Added proper CMD with Gunicorn in Dockerfile.

---

## Porter Deployment Configuration

### Current Settings (Keep These)
- **Entry Point:** `./backend`
- **Dockerfile Path:** `./Dockerfile`
- **Container Port:** `8080` ✅

### ⚠️ IMPORTANT: Update This Setting
**API Server Start Command:**
- ❌ OLD: `python app.py`
- ✅ NEW: **REMOVE THIS** (leave empty or delete)

**Why?** The Dockerfile now has a proper CMD that starts Gunicorn automatically. Porter should use the Dockerfile's CMD, not override it.

---

## Configuration Files

### 1. app.py
Updated to support both development and production:
```python
# Development: python app.py
# Production: Gunicorn (via Dockerfile CMD)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host='0.0.0.0', port=port, debug=debug)
```

### 2. gunicorn.conf.py
Production server configuration with sensible defaults:
- **Workers:** Auto-calculated based on CPU cores (2 x cores + 1)
- **Threads:** 2 per worker
- **Timeout:** 120 seconds (for long-running requests)
- **Binding:** `0.0.0.0:8080` (all interfaces)

### 3. Dockerfile
Multi-stage build with production CMD:
```dockerfile
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
```

---

## Environment Variables (Optional Tuning)

You can override Gunicorn settings via environment variables in Porter:

| Variable | Default | Description |
|----------|---------|-------------|
| `GUNICORN_WORKERS` | Auto (2×CPU+1) | Number of worker processes |
| `GUNICORN_THREADS` | 2 | Threads per worker |
| `GUNICORN_TIMEOUT` | 120 | Request timeout in seconds |
| `GUNICORN_LOG_LEVEL` | info | Logging level (debug, info, warning, error) |
| `FLASK_ENV` | production | Set to "development" for debug mode |

### Example: High-Traffic Configuration
If you need to handle more concurrent requests:
```
GUNICORN_WORKERS=8
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=180
```

### Example: Low-Resource Configuration
For smaller deployments:
```
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
```

---

## Deployment Steps

### 1. Push Changes to Git
```bash
cd /Users/aarav/Desktop/Aarav/Miscellaneous/Projects/hoptix
git add backend/app.py backend/gunicorn.conf.py backend/Dockerfile backend/DEPLOYMENT.md
git commit -m "Fix 502 error: Add production-ready Gunicorn setup"
git push origin main
```

### 2. Update Porter Configuration
1. Go to your Porter dashboard
2. Navigate to your backend service
3. **Remove or clear** the "API Server Start Command" field
4. Keep these settings:
   - Entry Point: `./backend`
   - Dockerfile Path: `./Dockerfile`
   - Container Port: `8080`
5. Save changes

### 3. Deploy
1. Trigger a new deployment in Porter
2. Watch the logs - you should see:
   ```
   [INFO] Starting gunicorn 21.2.0
   [INFO] Listening at: http://0.0.0.0:8080
   [INFO] Using worker: sync
   [INFO] Booting worker with pid: ...
   ```

### 4. Verify Deployment
Test the health endpoint:
```bash
curl https://your-backend-url.porter.run/health
# Expected response: {"status": "healthy", "service": "hoptix-backend"}
```

---

## Expected Log Output

### ✅ Successful Deployment Logs
```
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:8080 (1)
[INFO] Using worker: sync
[INFO] Booting worker with pid: 7
[INFO] Booting worker with pid: 8
[INFO] Booting worker with pid: 9
[INFO] Booting worker with pid: 10
```

### ❌ OLD Logs (Development Server)
```
WARNING: This is a development server. Do not use it in a production deployment.
Running on http://127.0.0.1:8080  ← BAD: localhost only!
```

---

## Troubleshooting

### Issue: Still Getting 502 Error
**Check:**
1. Porter is using the Dockerfile CMD (not overriding with `python app.py`)
2. Container port is set to `8080`
3. Logs show Gunicorn binding to `0.0.0.0:8080`

### Issue: Workers Crashing
**Possible causes:**
- Memory limits too low (increase in Porter)
- Too many workers for available CPU (reduce `GUNICORN_WORKERS`)
- Application errors (check error logs)

**Solution:**
```
GUNICORN_WORKERS=2  # Start with fewer workers
```

### Issue: Slow Response Times
**Possible causes:**
- Not enough workers/threads
- Long-running requests timing out

**Solution:**
```
GUNICORN_WORKERS=8
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=300  # 5 minutes
```

### Issue: Need to Debug
**Enable debug mode temporarily:**
```
FLASK_ENV=development
GUNICORN_LOG_LEVEL=debug
```

⚠️ **IMPORTANT:** Don't leave debug mode enabled in production!

---

## Performance Tuning

### Worker/Thread Calculation

**CPU-bound workloads** (heavy processing):
```
workers = (2 × CPU_cores) + 1
threads = 1-2
```

**I/O-bound workloads** (database, API calls):
```
workers = (2 × CPU_cores) + 1
threads = 2-4
```

**Current default:** Balanced configuration
```python
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
```

### Memory Considerations
Each worker consumes memory. Monitor your container:
- **2 workers:** ~500MB-1GB
- **4 workers:** ~1GB-2GB
- **8 workers:** ~2GB-4GB

Adjust Porter's memory limits accordingly.

---

## Local Development

### Running Locally with Flask Dev Server
```bash
cd backend
python app.py
# Starts on http://0.0.0.0:8080 with debug mode
```

### Testing Production Configuration Locally
```bash
cd backend
gunicorn --config gunicorn.conf.py app:app
# Runs exactly as it will in production
```

### Testing with Docker
```bash
cd backend
docker build -t hoptix-backend .
docker run -p 8080:8080 hoptix-backend
# Access at http://localhost:8080
```

---

## Security Notes

1. **Debug Mode:** Disabled in production via `FLASK_ENV=production`
2. **CORS:** Currently allows all origins (`*`) - consider restricting in production
3. **Non-root User:** Container runs as `appuser` (not root)
4. **No Secrets in Code:** All sensitive data should be in environment variables

---

## Monitoring

### Health Check Endpoints
- `GET /` - Simple "Hello, World!" response
- `GET /health` - JSON health status

### Log Monitoring
Gunicorn logs include:
- Access logs (HTTP requests)
- Error logs (application errors)
- Worker status (starts, crashes, restarts)

### Metrics to Watch
- Response times (in access logs)
- Error rate (5xx responses)
- Worker restarts (indicates crashes)
- Memory usage (via Porter dashboard)

---

## Rollback Plan

If deployment fails, rollback is simple:

1. In Porter, revert to previous deployment
2. Or temporarily set start command back to: `python app.py`
   (This will work but uses dev server)

---

## Next Steps

After successful deployment:

1. ✅ Verify `/health` endpoint responds
2. ✅ Test actual API endpoints
3. ✅ Monitor logs for errors
4. ✅ Check performance metrics
5. 🎯 Update frontend `NEXT_PUBLIC_BACKEND_URL` to point to new backend URL

---

## Questions?

If you encounter issues:
1. Check Porter logs for errors
2. Verify environment variables are set correctly
3. Test locally with Docker to reproduce
4. Review this deployment guide

Good luck with your deployment! 🚀
