"""
Configuration for chunked audio processing.
Adjust these parameters based on your system's memory and performance requirements.
"""

# Chunk processing configuration
CHUNK_SIZE_SECONDS = 300  # 5 minutes per chunk (reduced for better memory management)
SILENCE_THRESHOLD = -40   # dB threshold for silence detection
MIN_ACTIVE_DURATION = 5.0  # Minimum duration for active segments

# Memory management
MAX_MEMORY_MB = 500  # Reduced memory limit for deployment environments
CLEANUP_FREQUENCY = 3  # More frequent cleanup to prevent memory buildup

# Performance tuning
PARALLEL_CHUNKS = True  # Enable parallel processing for faster completion
MAX_WORKERS = 2  # Limited parallel workers to prevent resource exhaustion

# Audio processing
SAMPLE_RATE = 16000  # Target sample rate for processing
CHANNELS = 1  # Mono audio
AUDIO_FORMAT = "pcm_s16le"  # Audio format for ffmpeg processing

# Error handling
RETRY_FAILED_CHUNKS = True  # Retry failed chunks
MAX_RETRIES = 3  # Maximum number of retries per chunk
RETRY_DELAY = 5  # Delay between retries in seconds

# Logging and monitoring
VERBOSE_LOGGING = True  # Enable detailed logging
MEMORY_MONITORING = True  # Enable memory usage monitoring
PROGRESS_REPORTING = True  # Enable progress reporting

# Feature toggles
# Use the hoptix-style span segmentation pipeline (15s spans, per-span ASR)
# Set to False for large files to use chunking approach instead
USE_HOPTIX_SPAN_PIPELINE = False
