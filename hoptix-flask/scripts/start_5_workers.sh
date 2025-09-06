#!/bin/bash

# Start parallel workers script for Google Drive processing
# Automatically detects optimal number of workers based on CPU cores

# Detect number of CPU cores
CPU_CORES=$(sysctl -n hw.ncpu)
# Use 80% of cores, minimum 2, maximum 10 (to avoid overwhelming Google Drive API)
WORKER_COUNT=$(python3 -c "import math; cores=$CPU_CORES; print(max(2, min(10, int(cores * 0.8))))")

echo "🚀 Starting $WORKER_COUNT Parallel Video Processing Workers"
echo "🖥️  Detected $CPU_CORES CPU cores, using $WORKER_COUNT workers"
echo "========================================================="

# Validate required argument
if [ $# -eq 0 ]; then
    echo "❌ Error: Date argument required"
    echo "Usage: $0 YYYY-MM-DD"
    echo "Example: $0 2025-08-29"
    exit 1
fi

DATE_ARG=$1
echo "📅 Processing date: $DATE_ARG"

# Kill any existing workers first
echo "🧹 Cleaning up any existing workers..."
pkill -f "run_once.py" || true
pkill -f "run_parallel.py" || true
sleep 2

# Start parallel processing
echo "🔄 Starting parallel workers..."
python scripts/run_parallel.py --date "$DATE_ARG" --workers $WORKER_COUNT
