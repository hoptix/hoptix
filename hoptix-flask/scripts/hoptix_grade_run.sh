#!/bin/bash

# Grade all transactions for a given run_id in parallel workers

echo "📝 Hoptix Grade Run"
echo "===================="

export PYTHONUNBUFFERED=1

if [ $# -lt 1 ]; then
  echo "❌ Error: run_id required"
  echo "Usage: $0 RUN_ID [WORKERS]"
  echo "Example: $0 123e4567-e89b-12d3-a456-426614174000"
  echo "Example: $0 123e4567-e89b-12d3-a456-426614174000 8"
  exit 1
fi

RUN_ID=$1
WORKERS=${2:-11}

echo "🔄 Run ID: $RUN_ID"
echo "👥 Workers: $WORKERS"

# Change to the parent directory of this script
cd "$(dirname "$0")/.."

# Run the Python grading script
python3 scripts/grade_run.py "$RUN_ID" --workers "$WORKERS"

# Capture the exit code
EXIT_CODE=$?

echo "🎉 Grading complete for run $RUN_ID"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Grading completed successfully"
else
    echo "❌ Grading failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE

