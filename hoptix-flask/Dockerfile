# Use a specific Python version tag for better reproducibility
FROM python:3.11.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
# Install dependencies with --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary files to reduce image size
COPY app.py .
COPY config.py .
COPY integrations/ ./integrations/
COPY routes/ ./routes/
COPY services/ ./services/
COPY worker/ ./worker/
COPY commands/ ./commands/
COPY prompts/ ./prompts/

# Create a non-root user
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Create output directory with proper permissions
RUN mkdir -p /app/logs /app/exports && \
    chmod 755 /app/logs /app/exports && \
    chown -R appuser:appuser /app/logs /app/exports
USER appuser

# Set environment variables
ENV PYTHONPATH=/app

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "app:app"]

