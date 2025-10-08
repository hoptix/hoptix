#!/bin/bash

# Script to run audio processing with environment variable setup
# Usage: ./run_with_env.sh

set -e

echo "🎯 Audio Processing for Run 3afe854f-6cf6-403e-b2b2-77e039b6f8ca"
echo "=================================================================="

# Check if we're in the right directory
if [ ! -f "scripts/process_specific_run.py" ]; then
    echo "❌ Please run this script from the hoptix-flask directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please create it first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if environment variables are set
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "⚠️ Environment variables not set. Please set them:"
    echo ""
    echo "export SUPABASE_URL='https://your-project.supabase.co'"
    echo "export SUPABASE_SERVICE_KEY='your-service-key'"
    echo ""
    echo "Or run the interactive setup:"
    echo "python scripts/setup_and_run.py"
    exit 1
fi

echo "✅ Environment variables are set"
echo "📁 SUPABASE_URL: $SUPABASE_URL"
echo "🔑 SUPABASE_SERVICE_KEY: [HIDDEN]"

# Run the audio processing script
echo ""
echo "🚀 Starting audio processing..."
python scripts/process_specific_run.py

echo "🎉 Audio processing completed!"
