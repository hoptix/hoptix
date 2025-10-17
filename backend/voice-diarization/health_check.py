#!/usr/bin/env python3
"""
Health Check Server for Voice Diarization Service
Provides health, readiness, and metrics endpoints for monitoring
"""

import os
import threading
import json
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks."""

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass

    def do_GET(self):
        """Handle GET requests for health endpoints."""
        if self.path == '/health':
            self.handle_health()
        elif self.path == '/ready':
            self.handle_ready()
        elif self.path == '/metrics':
            self.handle_metrics()
        else:
            self.send_error(404, "Not Found")

    def handle_health(self):
        """Basic liveness check."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'voice-diarization'
        }
        self.wfile.write(json.dumps(response).encode())

    def handle_ready(self):
        """Readiness check - verify all dependencies are available."""
        checks = {}
        is_ready = True

        # Check PyTorch
        try:
            import torch
            checks['pytorch'] = {
                'status': 'ok',
                'version': torch.__version__,
                'cuda_available': torch.cuda.is_available()
            }
        except Exception as e:
            checks['pytorch'] = {'status': 'error', 'error': str(e)}
            is_ready = False

        # Check NeMo
        try:
            from nemo.collections.asr.models import EncDecSpeakerLabelModel
            checks['nemo'] = {'status': 'ok'}
        except Exception as e:
            checks['nemo'] = {'status': 'error', 'error': str(e)}
            is_ready = False

        # Check database connectivity
        try:
            if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SERVICE_KEY'):
                checks['database'] = {'status': 'ok'}
            else:
                checks['database'] = {'status': 'error', 'error': 'Missing credentials'}
                is_ready = False
        except Exception as e:
            checks['database'] = {'status': 'error', 'error': str(e)}
            is_ready = False

        # Check AssemblyAI
        try:
            if os.getenv('AAI_API_KEY'):
                checks['assemblyai'] = {'status': 'ok'}
            else:
                checks['assemblyai'] = {'status': 'error', 'error': 'Missing API key'}
                is_ready = False
        except Exception as e:
            checks['assemblyai'] = {'status': 'error', 'error': str(e)}
            is_ready = False

        status_code = 200 if is_ready else 503
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response = {
            'ready': is_ready,
            'checks': checks,
            'timestamp': datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())

    def handle_metrics(self):
        """Return system metrics."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            metrics = {
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory': {
                        'total_gb': memory.total / (1024**3),
                        'available_gb': memory.available / (1024**3),
                        'percent': memory.percent
                    },
                    'disk': {
                        'total_gb': disk.total / (1024**3),
                        'free_gb': disk.free / (1024**3),
                        'percent': disk.percent
                    }
                }
            }

            # Add GPU metrics if available
            try:
                import torch
                if torch.cuda.is_available():
                    metrics['gpu'] = {
                        'available': True,
                        'device_count': torch.cuda.device_count(),
                        'current_device': torch.cuda.current_device(),
                        'device_name': torch.cuda.get_device_name(0),
                        'memory_allocated_gb': torch.cuda.memory_allocated(0) / (1024**3),
                        'memory_reserved_gb': torch.cuda.memory_reserved(0) / (1024**3)
                    }
                else:
                    metrics['gpu'] = {'available': False}
            except:
                metrics['gpu'] = {'available': False}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode())

        except Exception as e:
            self.send_error(500, f"Error collecting metrics: {str(e)}")


def start_health_server(port: int = 8080) -> threading.Thread:
    """Start the health check server in a background thread."""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    logger.info(f"Health check server listening on port {port}")
    return thread


# For standalone testing
if __name__ == "__main__":
    import sys

    # Simple health check test when run directly
    if '--check' in sys.argv:
        import requests

        port = 8080
        try:
            # Check health endpoint
            response = requests.get(f'http://localhost:{port}/health', timeout=5)
            if response.status_code == 200:
                print("✅ Health check passed")
                print(json.dumps(response.json(), indent=2))
                sys.exit(0)
            else:
                print(f"❌ Health check failed: {response.status_code}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Health check error: {e}")
            sys.exit(1)
    else:
        # Run server for testing
        print("Starting health check server on port 8080...")
        print("Endpoints:")
        print("  - http://localhost:8080/health")
        print("  - http://localhost:8080/ready")
        print("  - http://localhost:8080/metrics")
        print("\nPress Ctrl+C to stop")

        server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
            sys.exit(0)