# ---- Python Builder Stage ----
    FROM python:3.11.12-slim AS builder

    WORKDIR /app

    # Install system dependencies for building
    RUN apt-get update && apt-get install -y \
        gcc \
        g++ \
        ffmpeg \
        && rm -rf /var/lib/apt/lists/*

    # Copy requirements first to leverage Docker cache
    # Note: Build context is repository root, so we specify backend/ prefix
    COPY backend/requirements.txt ./requirements.txt

    # Install PyTorch CPU-only version first (smaller size)
    RUN pip install --no-cache-dir torch==2.0.0+cpu torchaudio==2.0.0+cpu --index-url https://download.pytorch.org/whl/cpu

    # Install nemo-toolkit separately to handle memory constraints
    RUN pip install --no-cache-dir nemo-toolkit==1.21.0

    # Install remaining requirements
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy the rest of the Python application source from backend directory
    COPY backend/ ./
    
    # ---- Final Stage ----
    FROM python:3.11.12-slim AS final

    WORKDIR /app
    
    # Install runtime system dependencies
    RUN apt-get update && apt-get install -y \
        ffmpeg \
        && rm -rf /var/lib/apt/lists/* \
        && ffmpeg -version
    
    # Copy the Python environment from builder stage
    COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
    COPY --from=builder /usr/local/bin /usr/local/bin
    
    # Copy application files from builder stage
    COPY --from=builder /app/app.py /app/app.py
    COPY --from=builder /app/config.py /app/config.py
    COPY --from=builder /app/gunicorn.conf.py /app/gunicorn.conf.py
    COPY --from=builder /app/start.sh /app/start.sh
    COPY --from=builder /app/routes /app/routes
    COPY --from=builder /app/services /app/services
    COPY --from=builder /app/middleware /app/middleware
    COPY --from=builder /app/pipeline /app/pipeline
    COPY --from=builder /app/prompts /app/prompts
    COPY --from=builder /app/tests /app/tests
    COPY --from=builder /app/utils /app/utils
    COPY --from=builder /app/scripts /app/scripts

    # Ensure the scripts are executable
    RUN chmod +x /app/scripts/*.py /app/start.sh
    
    # Create a non-root user
    RUN useradd -m -s /bin/bash appuser && \
        chown -R appuser:appuser /app
    
    
    USER appuser

    # Set environment variables
    ENV PYTHONPATH=/app
    ENV PATH="/app/scripts:$PATH"
    ENV FLASK_ENV=production
    ENV IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg
    ENV FFMPEG_BINARY=/usr/bin/ffmpeg

    # Expose port
    EXPOSE 8080

    # Production-ready entrypoint using Gunicorn
    # Configuration is managed in gunicorn.conf.py
    # This allows easy tuning via environment variables without rebuilding the image
    CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]