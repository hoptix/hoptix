"""
Configuration for chunked audio processing.
Adjust these parameters based on your system's memory and performance requirements.
"""

# Chunk processing configuration
CHUNK_SIZE_SECONDS = 600  # 10 minutes per chunk
SILENCE_THRESHOLD = -40   # dB threshold for silence detection
MIN_ACTIVE_DURATION = 5.0  # Minimum duration for active segments

# Memory management
MAX_MEMORY_MB = 1000  # Maximum memory usage before forcing cleanup
CLEANUP_FREQUENCY = 5  # Force garbage collection every N chunks

# Performance tuning
PARALLEL_CHUNKS = True  # Set to True to process chunks in parallel (uses more memory)
MAX_WORKERS = 10  # Number of parallel workers if PARALLEL_CHUNKS is True

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
