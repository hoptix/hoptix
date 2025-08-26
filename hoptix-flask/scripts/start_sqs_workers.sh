#!/bin/bash

# Start multiple SQS workers script
echo "🚀 Starting SQS Video Processing Workers"
echo "========================================"

# Configuration
NUM_WORKERS=${1:-3}  # Default to 3 workers, can override with first argument
LOG_DIR="logs"

# Create logs directory
mkdir -p "$LOG_DIR"

# Kill any existing SQS workers first
echo "🧹 Cleaning up any existing SQS workers..."
pkill -f "sqs_worker.py" || true
sleep 2

# Check if SQS environment variables are set
if [ -z "$SQS_QUEUE_URL" ]; then
    echo "❌ Error: SQS_QUEUE_URL environment variable is not set"
    echo "Please set the following environment variables:"
    echo "  - SQS_QUEUE_URL"
    echo "  - SQS_DLQ_URL (optional)"
    exit 1
fi

echo "✅ SQS Queue URL: $SQS_QUEUE_URL"
if [ -n "$SQS_DLQ_URL" ]; then
    echo "✅ SQS DLQ URL: $SQS_DLQ_URL"
fi

# Start workers
echo "🔄 Starting $NUM_WORKERS SQS workers..."

for i in $(seq 1 $NUM_WORKERS); do
    WORKER_ID="sqs-worker-$i"
    LOG_FILE="$LOG_DIR/sqs_worker_$i.log"
    
    echo "   Starting $WORKER_ID..."
    python worker/sqs_worker.py --worker-id "$WORKER_ID" > "$LOG_FILE" 2>&1 &
    
    worker_pid=$!
    echo "   ✅ $WORKER_ID started (PID: $worker_pid)"
    
    # Small delay to avoid startup race conditions
    sleep 1
done

echo ""
echo "🎯 All $NUM_WORKERS SQS workers are running!"
echo "📊 Monitor logs: tail -f $LOG_DIR/sqs_worker_*.log"
echo "🛑 Stop all workers: ./scripts/stop_sqs_workers.sh"
echo ""

# Show running workers
echo "📋 Current SQS worker processes:"
ps aux | grep "sqs_worker.py" | grep -v grep

echo ""
echo "💡 Workers will automatically receive messages from SQS queue"
echo "   Use the Flask API /enqueue-videos to add videos to the queue"
echo "   Or use /enqueue-single-video for individual videos"
