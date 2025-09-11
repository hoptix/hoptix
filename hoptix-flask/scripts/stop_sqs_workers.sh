 worke#!/bin/bash

# Stop SQS workers script
echo "🛑 Stopping SQS Video Processing Workers"
echo "========================================"

# Find and stop SQS worker processes
WORKER_PIDS=$(pgrep -f "sqs_worker.py")

if [ -z "$WORKER_PIDS" ]; then
    echo "ℹ️  No SQS workers are currently running"
    exit 0
fi

echo "📋 Found SQS worker processes:"
ps aux | grep "sqs_worker.py" | grep -v grep

echo ""
echo "🔄 Sending graceful shutdown signal (SIGTERM)..."

# Send SIGTERM for graceful shutdown
for pid in $WORKER_PIDS; do
    echo "   Stopping worker PID $pid..."
    kill -TERM "$pid" 2>/dev/null
done

# Wait for graceful shutdown
echo "⏳ Waiting for workers to finish current jobs (max 60 seconds)..."
sleep 5

# Check if workers are still running
REMAINING_PIDS=$(pgrep -f "sqs_worker.py")

if [ -z "$REMAINING_PIDS" ]; then
    echo "✅ All SQS workers stopped gracefully"
else
    echo "⚠️  Some workers still running, sending SIGKILL..."
    
    for pid in $REMAINING_PIDS; do
        echo "   Force killing worker PID $pid..."
        kill -KILL "$pid" 2>/dev/null
    done
    
    sleep 2
    
    # Final check
    FINAL_PIDS=$(pgrep -f "sqs_worker.py")
    if [ -z "$FINAL_PIDS" ]; then
        echo "✅ All SQS workers stopped"
    else
        echo "❌ Some workers may still be running:"
        ps aux | grep "sqs_worker.py" | grep -v grep
    fi
fi

echo ""
echo "🧹 Cleanup complete"
