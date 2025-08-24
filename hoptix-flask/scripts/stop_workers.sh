#!/bin/bash

# Stop all workers script

echo "🛑 Stopping all video processing workers..."

# Find and kill all run_once.py processes
worker_pids=$(ps aux | grep "run_once.py" | grep -v grep | awk '{print $2}')

if [ -z "$worker_pids" ]; then
    echo "ℹ️ No workers currently running"
else
    echo "📋 Found workers with PIDs: $worker_pids"
    
    # Send SIGTERM first (graceful shutdown)
    echo "📤 Sending graceful shutdown signal..."
    for pid in $worker_pids; do
        kill -TERM $pid 2>/dev/null && echo "   ✅ Sent SIGTERM to PID $pid"
    done
    
    # Wait a moment for graceful shutdown
    sleep 5
    
    # Check if any are still running
    remaining_pids=$(ps aux | grep "run_once.py" | grep -v grep | awk '{print $2}')
    
    if [ ! -z "$remaining_pids" ]; then
        echo "⚠️ Some workers still running, forcing shutdown..."
        for pid in $remaining_pids; do
            kill -KILL $pid 2>/dev/null && echo "   💀 Force killed PID $pid"
        done
    fi
fi

# Also stop the threaded/multiprocessing workers if running
echo "🧹 Cleaning up other worker types..."
pkill -f "run_workers.py" 2>/dev/null && echo "   ✅ Stopped multiprocessing workers"
pkill -f "run_threaded_workers.py" 2>/dev/null && echo "   ✅ Stopped threaded workers"

echo "✅ All workers stopped"

# Show final status
remaining=$(ps aux | grep -E "(run_once|run_workers|run_threaded)" | grep -v grep)
if [ -z "$remaining" ]; then
    echo "✅ Confirmed: No workers are running"
else
    echo "⚠️ Warning: Some processes may still be running:"
    echo "$remaining"
fi
