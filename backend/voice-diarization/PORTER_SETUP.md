# Porter Dashboard Configuration

## Environment Variables to Set in Porter Dashboard

When deploying this service, configure these environment variables in the Porter dashboard:

### **Required Secrets** (Set in Secrets section)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
AAI_API_KEY=your-assemblyai-api-key
GOOGLE_DRIVE_CREDENTIALS={"type":"service_account","project_id":"..."}
```

### **Job Parameters** (Set in Environment Variables section)
```
LOCATION_ID=c3607cc3-0f0c-4725-9c42-eb2fdb5e016a
DATE=2025-10-06
```

### **Optional Tuning** (Already set with defaults in porter.yaml)
These are pre-configured but can be overridden if needed:
```
BATCH_SIZE=10
MAX_WORKERS=2
CONFIDENCE_THRESHOLD=0.75
```

## Cron Schedule Configuration

In the Porter dashboard, set the cron schedule for automatic runs:

**Recommended schedules:**
- Daily at 3 AM: `0 3 * * *`
- Daily at 2 AM: `0 2 * * *`
- Weekly on Sundays at 3 AM: `0 3 * * 0`
- Twice daily (6 AM and 6 PM): `0 6,18 * * *`

## Deployment Steps

1. **Deploy the application:**
   ```bash
   porter apply -f backend/porter.yaml
   ```

2. **In Porter Dashboard:**
   - Navigate to your application
   - Go to "Environment Variables" tab
   - Add all required secrets
   - Set job parameters (LOCATION_ID, DATE)
   - Save changes

3. **Set Cron Schedule:**
   - Go to "Jobs" or "Schedules" tab
   - Add cron expression (e.g., `0 3 * * *`)
   - Enable the schedule

4. **Manual Testing:**
   - Trigger a manual run to test
   - Check logs for success
   - Verify database updates

## Resource Allocation

The following resources are pre-configured in porter.yaml:
- **CPU Cores:** 2
- **RAM:** 4096 MB (4 GB)
- **GPU:** 1 NVIDIA GPU core
- **Timeout:** 3600 seconds (1 hour)
- **Retry Count:** 2
- **Retry Delay:** 300 seconds (5 minutes)

## Health Check Endpoints

Once deployed, the service exposes these endpoints:
- `http://[service-url]:8080/health` - Liveness check
- `http://[service-url]:8080/ready` - Readiness check (dependencies)
- `http://[service-url]:8080/metrics` - System metrics

## Monitoring

Check these in Porter dashboard:
- **Logs:** Real-time job execution logs
- **Metrics:** GPU usage, memory, CPU
- **Status:** Job success/failure rates
- **Duration:** Processing time per run

## Common Issues

### Job Fails with "Missing LOCATION_ID"
- Ensure `LOCATION_ID` is set in environment variables
- Verify it's a valid UUID format

### GPU Not Available
- Check GPU allocation in resource settings
- Verify CUDA drivers in logs
- May need to increase GPU cores to 1

### Out of Memory
- Reduce `BATCH_SIZE` to 5
- Reduce `MAX_WORKERS` to 1
- Increase RAM allocation

### Database Connection Failed
- Verify `SUPABASE_URL` is correct
- Check `SUPABASE_SERVICE_KEY` has permissions
- Test connection manually

## Support

For deployment issues:
1. Check logs in Porter dashboard
2. Review `backend/voice-diarization/DEPLOYMENT_GUIDE.md`
3. Test locally with `backend/voice-diarization/test_local.sh`