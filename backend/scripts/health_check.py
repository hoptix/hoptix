#!/usr/bin/env python3
"""
Health check endpoint for voice diarization service.
Can be used by Porter for monitoring job health.
"""

import os
import sys
import json
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.monitoring import MonitoringService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global monitoring service instance
monitor = MonitoringService()


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint."""

    def do_GET(self):
        """Handle GET requests for health check."""
        if self.path == '/health':
            self.send_health_response()
        elif self.path == '/ready':
            self.send_readiness_response()
        elif self.path == '/metrics':
            self.send_metrics_response()
        else:
            self.send_error(404)

    def send_health_response(self):
        """Send health check response."""
        try:
            health_status = monitor.get_health_status()

            # Determine HTTP status code
            if health_status['status'] == 'healthy':
                status_code = 200
            else:
                status_code = 503  # Service Unavailable

            # Send response
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_status).encode())

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.send_error(500, str(e))

    def send_readiness_response(self):
        """Send readiness check response."""
        try:
            # Check if all required services are available
            checks = {
                "database": self.check_database(),
                "google_drive": self.check_google_drive(),
                "assemblyai": self.check_assemblyai(),
                "gpu": self.check_gpu()
            }

            # All checks must pass for readiness
            is_ready = all(checks.values())

            response = {
                "ready": is_ready,
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat()
            }

            status_code = 200 if is_ready else 503
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            self.send_error(500, str(e))

    def send_metrics_response(self):
        """Send Prometheus-compatible metrics."""
        try:
            metrics = []

            # Job metrics
            metrics.append(f"# HELP voice_diarization_jobs_total Total number of jobs started")
            metrics.append(f"# TYPE voice_diarization_jobs_total counter")
            metrics.append(f"voice_diarization_jobs_total {monitor.metrics['job_starts']}")

            metrics.append(f"# HELP voice_diarization_jobs_completed_total Total number of jobs completed")
            metrics.append(f"# TYPE voice_diarization_jobs_completed_total counter")
            metrics.append(f"voice_diarization_jobs_completed_total {monitor.metrics['job_completions']}")

            metrics.append(f"# HELP voice_diarization_jobs_failed_total Total number of jobs failed")
            metrics.append(f"# TYPE voice_diarization_jobs_failed_total counter")
            metrics.append(f"voice_diarization_jobs_failed_total {monitor.metrics['job_failures']}")

            # Transaction metrics
            metrics.append(f"# HELP voice_diarization_transactions_processed_total Total transactions processed")
            metrics.append(f"# TYPE voice_diarization_transactions_processed_total counter")
            metrics.append(f"voice_diarization_transactions_processed_total {monitor.metrics['transactions_processed']}")

            metrics.append(f"# HELP voice_diarization_transactions_matched_total Total transactions matched")
            metrics.append(f"# TYPE voice_diarization_transactions_matched_total counter")
            metrics.append(f"voice_diarization_transactions_matched_total {monitor.metrics['transactions_matched']}")

            # API call metrics
            for api_name, stats in monitor.metrics["api_calls"].items():
                safe_name = api_name.replace("-", "_").replace(" ", "_")
                metrics.append(f"# HELP voice_diarization_api_{safe_name}_total Total {api_name} API calls")
                metrics.append(f"# TYPE voice_diarization_api_{safe_name}_total counter")
                metrics.append(f"voice_diarization_api_{safe_name}_total {stats['total']}")

                metrics.append(f"# HELP voice_diarization_api_{safe_name}_failures_total Failed {api_name} API calls")
                metrics.append(f"# TYPE voice_diarization_api_{safe_name}_failures_total counter")
                metrics.append(f"voice_diarization_api_{safe_name}_failures_total {stats['failures']}")

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write('\n'.join(metrics).encode())

        except Exception as e:
            logger.error(f"Metrics export failed: {e}")
            self.send_error(500, str(e))

    def check_database(self) -> bool:
        """Check database connectivity."""
        try:
            from services.database import Supa
            db = Supa()
            # Simple connectivity check
            result = db.client.table("workers").select("id").limit(1).execute()
            return result.data is not None
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False

    def check_google_drive(self) -> bool:
        """Check Google Drive connectivity."""
        try:
            from services.gdrive import GoogleDriveClient
            gdrive = GoogleDriveClient()
            # Check if we can initialize the client
            return gdrive is not None
        except Exception as e:
            logger.error(f"Google Drive check failed: {e}")
            return False

    def check_assemblyai(self) -> bool:
        """Check AssemblyAI configuration."""
        return bool(os.getenv("AAI_API_KEY"))

    def check_gpu(self) -> bool:
        """Check GPU availability."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_health_server(port: int = 8080):
    """Run health check HTTP server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Health check server listening on port {port}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down health check server")
        httpd.shutdown()


def run_in_background(port: int = 8080):
    """Run health check server in background thread."""
    thread = threading.Thread(target=run_health_server, args=(port,))
    thread.daemon = True
    thread.start()
    logger.info(f"Health check server started in background on port {port}")
    return thread


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voice Diarization Health Check Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--once", action="store_true", help="Run health check once and exit")

    args = parser.parse_args()

    if args.once:
        # Run single health check and exit
        health_status = monitor.get_health_status()
        print(json.dumps(health_status, indent=2))
        sys.exit(0 if health_status['status'] == 'healthy' else 1)
    else:
        # Run HTTP server
        run_health_server(args.port)