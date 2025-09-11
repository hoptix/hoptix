# Testing /run-one-video Endpoint

This guide explains how to test the `/run-one-video` endpoint using the provided test script.

## Prerequisites

1. **Environment Variables**: Make sure these are set in your `.env` file:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_KEY=your_service_key
   AWS_REGION=your_aws_region
   SQS_QUEUE_URL=your_sqs_queue_url
   SQS_DLQ_URL=your_dlq_url (optional)
   ```

2. **Flask App Running**: Start your Flask application:
   ```bash
   cd hoptix-flask
   python app.py
   ```

3. **Dependencies**: Make sure you have `requests` installed:
   ```bash
   pip install requests
   ```

## Running the Test

### Option 1: Automated Test Script
Run the comprehensive test script:
```bash
cd hoptix-flask/scripts
python test_run_one_video.py
```

This script will:
1. ✅ Check prerequisites (Flask app running, env vars set)
2. 🔧 Create test data (org, location, run, video)
3. 📤 Enqueue the video to SQS
4. 🧪 Test the `/run-one-video` endpoint
5. 🔍 Check the processing results
6. 🧹 Clean up test data

### Option 2: Manual Testing

#### Step 1: Create Test Data
First, create some test data in your database. You can use the existing seed script:
```bash
python scripts/seed_test_data.py
```

#### Step 2: Enqueue Videos to SQS
Use the Flask API to enqueue videos:
```bash
curl -X POST http://localhost:8000/enqueue-videos
```

Or enqueue a specific video:
```bash
curl -X POST http://localhost:8000/enqueue-single-video \
  -H "Content-Type: application/json" \
  -d '{"video_id": "your_video_id"}'
```

#### Step 3: Test the Endpoint
Call the run-one-video endpoint:
```bash
curl -X POST http://localhost:8000/runs/run-one-video
```

## Expected Results

### Success Response (200):
```json
{
  "message": "Video abc123 processed successfully"
}
```

### No Videos Available (404):
```json
{
  "error": "no videos to process"
}
```

### Processing Error (500):
```json
{
  "error": "Failed to process video: [error details]"
}
```

## Troubleshooting

### "Flask app is not running"
- Make sure you started the Flask app with `python app.py`
- Check that it's running on `http://localhost:8000`
- Verify the `/health` endpoint: `curl http://localhost:8000/health`

### "No videos to process"
- Check if there are videos in "uploaded" status in your database
- Enqueue some videos first using `/enqueue-videos`
- Check SQS queue stats: `curl http://localhost:8000/video-status`

### "SQS not configured"
- Verify `SQS_QUEUE_URL` is set in your environment
- Check AWS credentials are configured
- Test SQS connection with queue stats

### Processing Fails
- Check the Flask app logs for detailed error messages
- Verify S3 bucket access and file existence
- Check OpenAI API key if using transcription

## Queue Management

### Check Queue Status
```bash
curl http://localhost:8000/video-status
```

### Check Health
```bash
curl http://localhost:8000/health
```

### Process All Videos (Alternative)
If you want to process all videos directly without SQS:
```bash
curl -X POST http://localhost:8000/process-videos
```
