#!/bin/bash

# Test script to grade a single transaction to verify the system works
# before running the full batch grading.

echo "🧪 Hoptix Single Transaction Test"
echo "=================================="

export PYTHONUNBUFFERED=1

if [ $# -lt 1 ]; then
  echo "❌ Error: run_id required"
  echo "Usage: $0 RUN_ID [LOCATION_ID]"
  echo "Example: $0 123e4567-e89b-12d3-a456-426614174000"
  echo "Example: $0 123e4567-e89b-12d3-a456-426614174000 location_123"
  exit 1
fi

RUN_ID=$1
LOCATION_ID=$2

echo "🔄 Run ID: $RUN_ID"
if [ -n "$LOCATION_ID" ]; then
  echo "📍 Location ID: $LOCATION_ID"
else
  echo "📍 Location ID: Auto-detect"
fi

# Change to the parent directory of this script
cd "$(dirname "$0")/.."

# Run the Python test script
if [ -n "$LOCATION_ID" ]; then
  python3 scripts/test_single_transaction.py "$RUN_ID" --location-id "$LOCATION_ID"
else
  python3 scripts/test_single_transaction.py "$RUN_ID"
fi

# Capture the exit code
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "🎉 Test completed successfully!"
    echo "✅ The grading system is working correctly"
    echo "🚀 You can now run the full batch grading with:"
    echo "   ./scripts/hoptix_grade_run.sh $RUN_ID"
else
    echo "❌ Test failed!"
    echo "🔧 Please fix the issues before running full batch grading"
fi

exit $EXIT_CODE
