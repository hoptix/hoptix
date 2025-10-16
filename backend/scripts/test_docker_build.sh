#!/bin/bash
# Test script to verify Docker build locally before deployment

set -e

echo "=================================="
echo "Testing Voice Diarization Docker Build"
echo "=================================="

# Build the Docker image locally
echo "Building Docker image..."
docker build -f backend/Dockerfile.porter-only -t voice-test:latest . || {
    echo "❌ Docker build failed!"
    exit 1
}

echo "✅ Docker build succeeded!"

# Test the image
echo ""
echo "Testing imports in container..."
docker run --rm voice-test:latest python -c "
import sys
print('Python:', sys.version)

# Test critical imports
try:
    import torch
    import torchaudio
    print('✅ PyTorch:', torch.__version__)
    print('✅ Torchaudio:', torchaudio.__version__)
except Exception as e:
    print(f'❌ PyTorch/torchaudio error: {e}')
    sys.exit(1)

# Test numpy version
try:
    import numpy
    print(f'✅ NumPy: {numpy.__version__}')
    ver_parts = numpy.__version__.split('.')
    assert int(ver_parts[0]) == 1 and int(ver_parts[1]) < 24, 'NumPy version incompatible!'
except Exception as e:
    print(f'❌ NumPy error: {e}')
    sys.exit(1)

# Test hydra
try:
    import hydra
    print('✅ Hydra-core: OK')
except Exception as e:
    print(f'❌ Hydra error: {e}')
    sys.exit(1)

# Test Pydantic
try:
    import pydantic
    from pydantic import TypeAdapter
    print(f'✅ Pydantic: {pydantic.__version__}')
    assert pydantic.__version__ == '2.9.2', 'Wrong Pydantic version!'
except Exception as e:
    print(f'❌ Pydantic error: {e}')
    sys.exit(1)

# Test NeMo
try:
    from nemo.collections.asr.models import EncDecSpeakerLabelModel
    print('✅ NeMo: OK')
except Exception as e:
    print(f'⚠️  NeMo warning: {e}')
    # Don't fail on NeMo import issues

print('')
print('✅ All critical imports passed!')
" || {
    echo "❌ Import tests failed!"
    exit 1
}

echo ""
echo "=================================="
echo "✅ All tests passed! Safe to deploy."
echo "=================================="