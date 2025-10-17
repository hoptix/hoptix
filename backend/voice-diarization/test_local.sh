#!/bin/bash
# Local testing script for voice diarization service
# This script builds and tests the Docker container locally before deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Voice Diarization Local Testing Script${NC}"
echo -e "${GREEN}======================================${NC}"

# Check for required environment variables
check_env() {
    local var_name=$1
    if [ -z "${!var_name:-}" ]; then
        echo -e "${RED}❌ Error: $var_name is not set${NC}"
        echo "Please export $var_name before running this script"
        return 1
    else
        echo -e "${GREEN}✓${NC} $var_name is set"
    fi
}

echo -e "\n${YELLOW}Checking environment variables...${NC}"
check_env "SUPABASE_URL" || exit 1
check_env "SUPABASE_SERVICE_KEY" || exit 1
check_env "AAI_API_KEY" || exit 1
check_env "LOCATION_ID" || exit 1
check_env "DATE" || exit 1

# Optional: Check for Google Drive credentials
if [ -z "${GOOGLE_DRIVE_CREDENTIALS:-}" ] && [ ! -f "credentials.json" ]; then
    echo -e "${YELLOW}⚠️  Warning: GOOGLE_DRIVE_CREDENTIALS not set and credentials.json not found${NC}"
    echo "Google Drive integration may not work"
fi

# Build the Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -f Dockerfile -t voice-diarization-test:latest . || {
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
}

echo -e "${GREEN}✅ Docker image built successfully${NC}"

# Check if GPU is available
echo -e "\n${YELLOW}Checking for GPU availability...${NC}"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
    GPU_FLAG="--gpus all"
    echo -e "${GREEN}✅ GPU detected, will use GPU acceleration${NC}"
else
    GPU_FLAG=""
    echo -e "${YELLOW}⚠️  No GPU detected, will use CPU (slower)${NC}"
fi

# Run health check
echo -e "\n${YELLOW}Running health check...${NC}"
docker run --rm \
    ${GPU_FLAG} \
    -e SUPABASE_URL="$SUPABASE_URL" \
    -e SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" \
    -e AAI_API_KEY="$AAI_API_KEY" \
    -e GOOGLE_DRIVE_CREDENTIALS="${GOOGLE_DRIVE_CREDENTIALS:-}" \
    voice-diarization-test:latest \
    python health_check.py --check || {
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
}

echo -e "${GREEN}✅ Health check passed${NC}"

# Run dry run
echo -e "\n${YELLOW}Running dry run test...${NC}"
docker run --rm \
    ${GPU_FLAG} \
    -e SUPABASE_URL="$SUPABASE_URL" \
    -e SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" \
    -e AAI_API_KEY="$AAI_API_KEY" \
    -e GOOGLE_DRIVE_CREDENTIALS="${GOOGLE_DRIVE_CREDENTIALS:-}" \
    -e LOCATION_ID="$LOCATION_ID" \
    -e DATE="$DATE" \
    -e BATCH_SIZE="${BATCH_SIZE:-10}" \
    -e MAX_WORKERS="${MAX_WORKERS:-2}" \
    voice-diarization-test:latest \
    python voice_job.py --dry-run

echo -e "${GREEN}✅ Dry run completed successfully${NC}"

# Option to run full test
echo -e "\n${YELLOW}Ready to run full test?${NC}"
echo "This will process actual data for location $LOCATION_ID on date $DATE"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Running full test...${NC}"

    docker run --rm \
        ${GPU_FLAG} \
        -e SUPABASE_URL="$SUPABASE_URL" \
        -e SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" \
        -e AAI_API_KEY="$AAI_API_KEY" \
        -e GOOGLE_DRIVE_CREDENTIALS="${GOOGLE_DRIVE_CREDENTIALS:-}" \
        -e LOCATION_ID="$LOCATION_ID" \
        -e DATE="$DATE" \
        -e BATCH_SIZE="${BATCH_SIZE:-10}" \
        -e MAX_WORKERS="${MAX_WORKERS:-2}" \
        -e HEALTH_CHECK_PORT="8080" \
        -p 8080:8080 \
        voice-diarization-test:latest

    echo -e "${GREEN}✅ Full test completed${NC}"
else
    echo -e "${YELLOW}Skipping full test${NC}"
fi

echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}Local testing complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo
echo "Next steps:"
echo "1. Review the test results above"
echo "2. If successful, deploy to Porter with:"
echo "   porter apply -f porter.yaml"
echo "3. Configure environment variables in Porter dashboard"
echo "4. Set up cron schedule in Porter dashboard"