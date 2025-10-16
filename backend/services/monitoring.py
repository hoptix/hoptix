"""
Monitoring and alerting service for voice diarization jobs.
Provides health checks, metrics tracking, and alerting capabilities.
"""

import os
import json
import time
import logging
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from functools import wraps
import requests

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring voice diarization job health and metrics."""

    def __init__(self):
        """Initialize monitoring service with optional webhook/Slack configuration."""
        # Webhook URLs for alerting (configure in environment)
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.generic_webhook = os.getenv("MONITORING_WEBHOOK_URL")

        # Metrics storage (in production, use a proper metrics store)
        self.metrics = {
            "job_starts": 0,
            "job_completions": 0,
            "job_failures": 0,
            "transactions_processed": 0,
            "transactions_matched": 0,
            "transactions_no_match": 0,
            "api_calls": {},
            "errors": [],
            "last_successful_run": None
        }

        # Performance thresholds
        self.thresholds = {
            "max_job_duration_seconds": int(os.getenv("MAX_JOB_DURATION", "21600")),  # 6 hours
            "max_memory_gb": float(os.getenv("MAX_MEMORY_GB", "7.5")),
            "min_success_rate": float(os.getenv("MIN_SUCCESS_RATE", "0.7")),
            "max_api_failures": int(os.getenv("MAX_API_FAILURES", "10"))
        }

    def start_job(self, location_id: str, date: str) -> Dict[str, Any]:
        """Record job start and return job metadata."""
        job_id = f"{location_id}_{date}_{int(time.time())}"

        self.metrics["job_starts"] += 1

        job_metadata = {
            "job_id": job_id,
            "location_id": location_id,
            "date": date,
            "start_time": datetime.utcnow().isoformat(),
            "status": "running"
        }

        # Send start notification for important jobs
        if os.getenv("NOTIFY_JOB_START") == "true":
            self.send_alert(
                level="info",
                title="Voice Diarization Job Started",
                message=f"Processing location {location_id} for date {date}",
                metadata=job_metadata
            )

        return job_metadata

    def complete_job(self, job_metadata: Dict[str, Any], stats: Dict[str, int]):
        """Record successful job completion with statistics."""
        job_metadata["end_time"] = datetime.utcnow().isoformat()
        job_metadata["status"] = "completed"
        job_metadata["stats"] = stats

        # Calculate duration
        start = datetime.fromisoformat(job_metadata["start_time"])
        end = datetime.fromisoformat(job_metadata["end_time"])
        duration = (end - start).total_seconds()
        job_metadata["duration_seconds"] = duration

        # Update metrics
        self.metrics["job_completions"] += 1
        self.metrics["last_successful_run"] = job_metadata["end_time"]
        self.metrics["transactions_processed"] += stats.get("processed", 0)
        self.metrics["transactions_matched"] += stats.get("updated", 0)
        self.metrics["transactions_no_match"] += stats.get("no_match", 0)

        # Check for performance issues
        if duration > self.thresholds["max_job_duration_seconds"]:
            self.send_alert(
                level="warning",
                title="Slow Job Detected",
                message=f"Job took {duration/3600:.1f} hours (threshold: {self.thresholds['max_job_duration_seconds']/3600:.1f}h)",
                metadata=job_metadata
            )

        # Send completion notification
        success_rate = stats.get("updated", 0) / max(stats.get("processed", 1), 1)

        if success_rate < self.thresholds["min_success_rate"]:
            self.send_alert(
                level="warning",
                title="Low Match Rate",
                message=f"Only {success_rate*100:.1f}% of transactions matched (threshold: {self.thresholds['min_success_rate']*100}%)",
                metadata=job_metadata
            )
        else:
            logger.info(f"Job completed successfully: {job_metadata['job_id']}")

    def fail_job(self, job_metadata: Dict[str, Any], error: Exception):
        """Record job failure with error details."""
        job_metadata["end_time"] = datetime.utcnow().isoformat()
        job_metadata["status"] = "failed"
        job_metadata["error"] = str(error)
        job_metadata["error_type"] = type(error).__name__
        job_metadata["traceback"] = traceback.format_exc()

        # Update metrics
        self.metrics["job_failures"] += 1
        self.metrics["errors"].append({
            "timestamp": job_metadata["end_time"],
            "job_id": job_metadata["job_id"],
            "error": str(error),
            "type": type(error).__name__
        })

        # Keep only last 100 errors
        self.metrics["errors"] = self.metrics["errors"][-100:]

        # Send failure alert
        self.send_alert(
            level="error",
            title="Voice Diarization Job Failed",
            message=f"Job {job_metadata['job_id']} failed: {error}",
            metadata=job_metadata
        )

    def track_api_call(self, api_name: str, success: bool, duration_ms: float):
        """Track external API call metrics."""
        if api_name not in self.metrics["api_calls"]:
            self.metrics["api_calls"][api_name] = {
                "total": 0,
                "success": 0,
                "failures": 0,
                "total_duration_ms": 0
            }

        self.metrics["api_calls"][api_name]["total"] += 1
        if success:
            self.metrics["api_calls"][api_name]["success"] += 1
        else:
            self.metrics["api_calls"][api_name]["failures"] += 1
        self.metrics["api_calls"][api_name]["total_duration_ms"] += duration_ms

        # Check failure threshold
        if self.metrics["api_calls"][api_name]["failures"] > self.thresholds["max_api_failures"]:
            self.send_alert(
                level="error",
                title=f"High API Failure Rate: {api_name}",
                message=f"{api_name} has failed {self.metrics['api_calls'][api_name]['failures']} times",
                metadata={"api_metrics": self.metrics["api_calls"][api_name]}
            )

    def check_memory_usage(self) -> Dict[str, float]:
        """Check current memory usage and alert if threshold exceeded."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_gb = memory_info.rss / (1024 ** 3)

            memory_stats = {
                "memory_gb": memory_gb,
                "threshold_gb": self.thresholds["max_memory_gb"],
                "percentage": (memory_gb / self.thresholds["max_memory_gb"]) * 100
            }

            if memory_gb > self.thresholds["max_memory_gb"]:
                self.send_alert(
                    level="warning",
                    title="High Memory Usage",
                    message=f"Using {memory_gb:.2f} GB of memory (threshold: {self.thresholds['max_memory_gb']} GB)",
                    metadata=memory_stats
                )

            return memory_stats

        except ImportError:
            logger.warning("psutil not installed, cannot check memory usage")
            return {}

    def send_alert(self, level: str, title: str, message: str, metadata: Optional[Dict] = None):
        """Send alert to configured webhook endpoints."""
        # Log locally first
        log_message = f"[{level.upper()}] {title}: {message}"
        if level == "error":
            logger.error(log_message)
        elif level == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Send to Slack
        if self.slack_webhook:
            self._send_slack_alert(level, title, message, metadata)

        # Send to Discord
        if self.discord_webhook:
            self._send_discord_alert(level, title, message, metadata)

        # Send to generic webhook
        if self.generic_webhook:
            self._send_generic_alert(level, title, message, metadata)

    def _send_slack_alert(self, level: str, title: str, message: str, metadata: Optional[Dict]):
        """Send alert to Slack webhook."""
        color = {
            "error": "danger",
            "warning": "warning",
            "info": "good"
        }.get(level, "#808080")

        payload = {
            "attachments": [{
                "color": color,
                "title": title,
                "text": message,
                "footer": "Voice Diarization Monitor",
                "ts": int(time.time())
            }]
        }

        if metadata:
            payload["attachments"][0]["fields"] = [
                {"title": k, "value": str(v), "short": True}
                for k, v in metadata.items()
                if k not in ["traceback", "error"]
            ]

        try:
            response = requests.post(self.slack_webhook, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    def _send_discord_alert(self, level: str, title: str, message: str, metadata: Optional[Dict]):
        """Send alert to Discord webhook."""
        color = {
            "error": 0xFF0000,    # Red
            "warning": 0xFFA500,  # Orange
            "info": 0x00FF00      # Green
        }.get(level, 0x808080)

        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
                "footer": {"text": "Voice Diarization Monitor"},
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

        if metadata:
            payload["embeds"][0]["fields"] = [
                {"name": k, "value": str(v)[:1024], "inline": True}
                for k, v in metadata.items()
                if k not in ["traceback", "error"]
            ]

        try:
            response = requests.post(self.discord_webhook, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")

    def _send_generic_alert(self, level: str, title: str, message: str, metadata: Optional[Dict]):
        """Send alert to generic webhook endpoint."""
        payload = {
            "level": level,
            "title": title,
            "message": message,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "service": "voice-diarization"
        }

        try:
            response = requests.post(self.generic_webhook, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send generic alert: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of the voice diarization system."""
        now = datetime.utcnow()

        # Calculate success rate
        total_jobs = self.metrics["job_starts"]
        if total_jobs > 0:
            job_success_rate = self.metrics["job_completions"] / total_jobs
        else:
            job_success_rate = 1.0

        # Check if system is healthy
        is_healthy = True
        health_issues = []

        # Check recent failures
        recent_errors = [e for e in self.metrics["errors"]
                        if datetime.fromisoformat(e["timestamp"]) > now - timedelta(hours=1)]
        if len(recent_errors) > 5:
            is_healthy = False
            health_issues.append(f"{len(recent_errors)} errors in the last hour")

        # Check job success rate
        if job_success_rate < 0.8 and total_jobs > 5:
            is_healthy = False
            health_issues.append(f"Low job success rate: {job_success_rate*100:.1f}%")

        # Check last successful run
        if self.metrics["last_successful_run"]:
            last_run = datetime.fromisoformat(self.metrics["last_successful_run"])
            hours_since = (now - last_run).total_seconds() / 3600
            if hours_since > 24:
                health_issues.append(f"No successful runs in {hours_since:.1f} hours")

        # Get memory usage
        memory_stats = self.check_memory_usage()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "issues": health_issues,
            "metrics": {
                "job_success_rate": job_success_rate,
                "total_jobs": total_jobs,
                "recent_errors": len(recent_errors),
                "memory_gb": memory_stats.get("memory_gb", 0),
                "last_successful_run": self.metrics["last_successful_run"]
            },
            "timestamp": now.isoformat()
        }


# Decorator for retry logic with monitoring
def retry_with_monitoring(monitor: Optional[MonitoringService] = None,
                         api_name: str = "external_api",
                         max_retries: int = 3,
                         backoff_base: int = 2):
    """Decorator to add retry logic with monitoring to functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            last_exception = None

            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)

                    # Track successful API call
                    if monitor:
                        duration_ms = (time.time() - start_time) * 1000
                        monitor.track_api_call(api_name, True, duration_ms)

                    return result

                except Exception as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        # Exponential backoff
                        wait_time = backoff_base ** attempt
                        logger.warning(f"{api_name} attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        # Track failed API call
                        if monitor:
                            duration_ms = (time.time() - start_time) * 1000
                            monitor.track_api_call(api_name, False, duration_ms)

                        # Re-raise the exception
                        raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# Health check endpoint function
def get_health_endpoint():
    """Function to expose health status as an HTTP endpoint."""
    monitor = MonitoringService()
    return monitor.get_health_status()