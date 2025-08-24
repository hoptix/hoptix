#!/bin/bash

# Start 5 workers script
# This script starts 5 separate instances of the video processor

echo "🚀 Starting 5 Video Processing Workers"
echo "====================================="

# Kill any existing workers first
echo "🧹 Cleaning up any existing workers..."
pkill -f "run_once.py" || true
sleep 2

# Start 5 workers in background
echo "🔄 Starting workers..."

for i in {1..5}; do
    echo "   Starting Worker $i..."
    python scripts/run_once.py > "worker_${i}.log" 2>&1 &
    worker_pid=$!
    echo "   ✅ Worker $i started (PID: $worker_pid)"
    
    # Small delay to avoid race conditions on startup
    sleep 1
done

echo ""
echo "🎯 All 5 workers are running!"
echo "📊 Monitor logs: tail -f worker_1.log worker_2.log worker_3.log worker_4.log worker_5.log"
echo "🛑 Stop all workers: ./scripts/stop_workers.sh"
echo ""

# Show running workers
echo "📋 Current worker processes:"
ps aux | grep "run_once.py" | grep -v grep

echo ""
echo "💡 Workers will automatically stop when no more videos are available"
echo "   or you can stop them manually with: pkill -f run_once.py"
