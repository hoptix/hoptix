# # Voice Diarization Service - Optimized Multi-Stage Dockerfile
# # Builds a minimal, GPU-enabled container for voice diarization with TitaNet
# # Version: 2.0.5 - Use system Python with PYTHONPATH to venv packages

# # Stage 1: Dependencies Builder
# FROM python:3.10-slim AS deps-builder

# # Set build environment
# ENV DEBIAN_FRONTEND=noninteractive \
#     PIP_NO_CACHE_DIR=1 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1 \
#     PYTHONDONTWRITEBYTECODE=1

# # Install build dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     g++ \
#     make \
#     cmake \
#     ffmpeg \
#     libsndfile1-dev \
#     && rm -rf /var/lib/apt/lists/*

# # Create virtual environment for isolation
# RUN python -m venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# # Upgrade pip and install wheel
# RUN pip install --upgrade pip setuptools wheel

# # Copy requirements files (from backend/voice-diarization/ since build context is repo root)
# COPY backend/voice-diarization/requirements-voice-core.txt backend/voice-diarization/requirements-voice-nemo.txt /tmp/

# # Install PyTorch with CUDA 11.7 support FIRST (critical for GPU)
# RUN pip install torch==2.0.1+cu117 torchaudio==2.0.2+cu117 \
#     --index-url https://download.pytorch.org/whl/cu117

# # Install core dependencies
# RUN pip install -r /tmp/requirements-voice-core.txt

# # Verify PyTorch installation
# RUN python -c "import torch; print(f'PyTorch {torch.__version__} with CUDA {torch.version.cuda}')"

# # Stage 2: NeMo Builder (separate to handle conflicts)
# FROM deps-builder AS nemo-builder

# # Install NeMo dependencies carefully
# RUN pip install hydra-core==1.3.2 omegaconf==2.3.0 pytorch-lightning==2.0.0

# # Install Cython first (required for youtokentome and other packages that NeMo will install)
# RUN pip install Cython>=3.0.0

# # Install NeMo with all dependencies (Cython now available for building)
# RUN pip install nemo-toolkit[asr]==1.21.0

# # Install remaining NeMo requirements (including previously missing dependencies)
# RUN pip install \
#     huggingface-hub==0.23.5 \
#     onnx>=1.7.0 \
#     ruamel.yaml \
#     wget>=3.2 \
#     text-unidecode \
#     youtokentome>=1.0.6 \
#     sentencepiece>=0.1.99 \
#     webdataset \
#     braceexpand \
#     editdistance \
#     g2p-en \
#     inflect \
#     jiwer \
#     kaldi-io \
#     kaldiio \
#     matplotlib \
#     packaging \
#     pesq \
#     pystoi \
#     sacremoses \
#     sox \
#     tensorboard \
#     wrapt

# # Verify NeMo installation
# RUN python -c "from nemo.collections.asr.models import EncDecSpeakerLabelModel; print('✓ NeMo ASR models OK')"

# # Stage 3: Runtime (minimal final image with GPU support)
# FROM nvidia/cuda:11.7.1-runtime-ubuntu22.04 AS runtime

# # Install Python and runtime dependencies only
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     python3.10 \
#     python3.10-venv \
#     ffmpeg \
#     libsndfile1 \
#     && rm -rf /var/lib/apt/lists/* \
#     && ln -s /usr/bin/python3.10 /usr/bin/python

# # Copy virtual environment from builder
# COPY --from=nemo-builder /opt/venv /opt/venv

# # Set environment
# # Use system Python but point to venv's packages
# ENV PYTHONPATH="/opt/venv/lib/python3.10/site-packages" \
#     PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1 \
#     CUDA_VISIBLE_DEVICES=0 \
#     PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"

# # Create app directory and user
# WORKDIR /app
# RUN useradd -m -u 1000 -s /bin/bash voiceuser && \
#     chown -R voiceuser:voiceuser /app

# # Copy application code (from backend/voice-diarization/ since build context is repo root)
# COPY --chown=voiceuser:voiceuser backend/voice-diarization/voice_job.py backend/voice-diarization/health_check.py /app/
# COPY --chown=voiceuser:voiceuser backend/voice-diarization/services/ /app/services/
# COPY --chown=voiceuser:voiceuser backend/voice-diarization/pipeline/ /app/pipeline/

# # Switch to non-root user
# USER voiceuser

# # Health check (use system Python with PYTHONPATH set to venv packages)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python health_check.py || exit 1

# # Entry point (use system Python with PYTHONPATH pointing to venv packages)
# ENTRYPOINT ["python", "-u"]
# CMD ["voice_job.py"]



# syntax=docker/dockerfile:1

# ============================================================
# Stage 1: Build wheels & compile native deps on the SAME base
# ============================================================
FROM nvidia/cuda:11.7.1-runtime-ubuntu22.04 AS build

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3-pip python3-dev \
    gcc g++ make cmake \
    ffmpeg libsndfile1-dev sox \
  && rm -rf /var/lib/apt/lists/* \
  && ln -sf /usr/bin/python3.10 /usr/bin/python

# Create isolated venv INSIDE the target base
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Base Python build tooling
RUN pip install --upgrade pip setuptools wheel

# Torch (CUDA 11.7) first to ensure correct CUDA ABI
RUN pip install torch==2.0.1+cu117 torchaudio==2.0.2+cu117 \
    --index-url https://download.pytorch.org/whl/cu117

# Copy requirements and install core deps
COPY backend/voice-diarization/requirements-voice-core.txt /tmp/requirements-voice-core.txt
RUN pip install -r /tmp/requirements-voice-core.txt

# NeMo stack (versions pinned for compatibility with Torch 2.0.x)
RUN pip install hydra-core==1.3.2 omegaconf==2.3.0 pytorch-lightning==2.0.0
RUN pip install "Cython>=3.0.0"
RUN pip install "nemo-toolkit[asr]==1.21.0"
RUN pip install \
    "huggingface-hub==0.23.5" onnx>=1.7.0 ruamel.yaml wget>=3.2 text-unidecode \
    youtokentome>=1.0.6 sentencepiece>=0.1.99 webdataset braceexpand editdistance \
    g2p-en inflect jiwer kaldi-io kaldiio matplotlib packaging pesq pystoi \
    sacremoses sox tensorboard wrapt

# Smoke test build-time imports
RUN python -c "import torch;print(torch.__version__, torch.version.cuda);import nemo.collections.asr as asr;print('NeMo OK')"

# ==============================================
# Stage 2: Runtime = same base; copy venv + app
# ==============================================
FROM nvidia/cuda:11.7.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv \
    ffmpeg libsndfile1 sox \
  && rm -rf /var/lib/apt/lists/* \
  && ln -sf /usr/bin/python3.10 /usr/bin/python

# NVIDIA Container Toolkit runtime envs
# (let the runtime enumerate devices; don't pin CUDA_VISIBLE_DEVICES here)
ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Optional: cache dirs (mount a volume here to speed cold starts)
ENV HF_HOME=/home/voiceuser/.cache/huggingface \
    TORCH_HOME=/home/voiceuser/.cache/torch

# Non-root user and workdir
RUN useradd -m -u 1000 -s /bin/bash voiceuser
USER voiceuser
WORKDIR /app

# Copy venv from build stage and app code
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY --chown=voiceuser:voiceuser backend/voice-diarization/voice_job.py backend/voice-diarization/health_check.py /app/
COPY --chown=voiceuser:voiceuser backend/voice-diarization/services/ /app/services/
COPY --chown=voiceuser:voiceuser backend/voice-diarization/pipeline/ /app/pipeline/

# Jobs run to completion; healthcheck not required for CronJobs
# Use absolute path to be unambiguous
ENTRYPOINT ["/opt/venv/bin/python", "-u", "/app/voice_job.py"]
