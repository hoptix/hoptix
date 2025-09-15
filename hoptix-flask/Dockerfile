# ---- Python Builder Stage ----
FROM python:3.11.12-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Python application source
COPY . ./

# ---- Final Stage ----
FROM python:3.11.12-slim AS final

WORKDIR /app

# Copy the Python environment from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files from builder stage
COPY --from=builder /app/app.py /app/app.py
COPY --from=builder /app/config.py /app/config.py
COPY --from=builder /app/integrations /app/integrations
COPY --from=builder /app/routes /app/routes
COPY --from=builder /app/services /app/services
COPY --from=builder /app/worker /app/worker
COPY --from=builder /app/commands /app/commands
COPY --from=builder /app/prompts /app/prompts
COPY --from=builder /app/scripts /app/scripts

# Ensure the scripts are executable
RUN chmod +x /app/scripts/*.sh
RUN chmod +x /app/scripts/*.py

# Create a non-root user
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app


USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH="/app/scripts:$PATH"

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "app:app"]

