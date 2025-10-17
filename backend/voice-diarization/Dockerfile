# Voice Diarization Service - Optimized Multi-Stage Dockerfile
# Builds a minimal, GPU-enabled container for voice diarization with TitaNet
# Version: 2.0.3 - Install Cython before NeMo for correct build order

# Stage 1: Dependencies Builder
FROM python:3.10-slim AS deps-builder

# Set build environment
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    cmake \
    ffmpeg \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements files (from backend/voice-diarization/ since build context is repo root)
COPY backend/voice-diarization/requirements-voice-core.txt backend/voice-diarization/requirements-voice-nemo.txt /tmp/

# Install PyTorch with CUDA 11.7 support FIRST (critical for GPU)
RUN pip install torch==2.0.1+cu117 torchaudio==2.0.2+cu117 \
    --index-url https://download.pytorch.org/whl/cu117

# Install core dependencies
RUN pip install -r /tmp/requirements-voice-core.txt

# Verify PyTorch installation
RUN python -c "import torch; print(f'PyTorch {torch.__version__} with CUDA {torch.version.cuda}')"

# Stage 2: NeMo Builder (separate to handle conflicts)
FROM deps-builder AS nemo-builder

# Install NeMo dependencies carefully
RUN pip install hydra-core==1.3.2 omegaconf==2.3.0 pytorch-lightning==2.0.0

# Install Cython first (required for youtokentome and other packages that NeMo will install)
RUN pip install Cython>=3.0.0

# Install NeMo with all dependencies (Cython now available for building)
RUN pip install nemo-toolkit[asr]==1.21.0

# Install remaining NeMo requirements (including previously missing dependencies)
RUN pip install \
    huggingface-hub==0.23.5 \
    onnx>=1.7.0 \
    ruamel.yaml \
    wget>=3.2 \
    text-unidecode \
    youtokentome>=1.0.6 \
    sentencepiece>=0.1.99 \
    webdataset \
    braceexpand \
    editdistance \
    g2p-en \
    inflect \
    jiwer \
    kaldi-io \
    kaldiio \
    matplotlib \
    packaging \
    pesq \
    pystoi \
    sacremoses \
    sox \
    tensorboard \
    wrapt

# Verify NeMo installation
RUN python -c "from nemo.collections.asr.models import EncDecSpeakerLabelModel; print('✓ NeMo ASR models OK')"

# Stage 3: Runtime (minimal final image with GPU support)
FROM nvidia/cuda:11.7.1-runtime-ubuntu22.04 AS runtime

# Install Python and runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.10 /usr/bin/python

# Copy virtual environment from builder
COPY --from=nemo-builder /opt/venv /opt/venv

# Set environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CUDA_VISIBLE_DEVICES=0 \
    PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"

# Create app directory and user
WORKDIR /app
RUN useradd -m -u 1000 -s /bin/bash voiceuser && \
    chown -R voiceuser:voiceuser /app

# Copy application code (from backend/voice-diarization/ since build context is repo root)
COPY --chown=voiceuser:voiceuser backend/voice-diarization/voice_job.py backend/voice-diarization/health_check.py /app/
COPY --chown=voiceuser:voiceuser backend/voice-diarization/services/ /app/services/
COPY --chown=voiceuser:voiceuser backend/voice-diarization/pipeline/ /app/pipeline/

# Switch to non-root user
USER voiceuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python health_check.py || exit 1

# Entry point
ENTRYPOINT ["python", "-u"]
CMD ["voice_job.py"]