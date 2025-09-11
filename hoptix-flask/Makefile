# Hoptix Flask Server - Docker Makefile

.PHONY: help build up down logs clean restart shell test

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - View logs from all services"
	@echo "  restart   - Restart all services"
	@echo "  shell     - Open shell in Flask container"
	@echo "  test      - Test the health endpoint"
	@echo "  clean     - Clean up Docker resources"
	@echo "  scale     - Scale workers (usage: make scale WORKERS=3)"

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Start with build
up-build:
	docker-compose up -d --build

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# View logs for specific service
logs-flask:
	docker-compose logs -f hoptix-flask

logs-worker:
	docker-compose logs -f hoptix-worker

# Restart services
restart:
	docker-compose restart

# Open shell in Flask container
shell:
	docker-compose exec hoptix-flask bash

# Test health endpoint
test:
	@echo "Testing health endpoint..."
	@curl -f http://localhost:8000/health || echo "Health check failed"

# Scale workers (usage: make scale WORKERS=3)
WORKERS ?= 2
scale:
	docker-compose up -d --scale hoptix-worker=$(WORKERS)

# Clean up Docker resources
clean:
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# Show container status
status:
	docker-compose ps

# View container resource usage
stats:
	docker stats

# Setup environment (copy template)
setup:
	@if [ ! -f .env ]; then \
		cp env.template .env; \
		echo "Created .env file from template. Please edit it with your values."; \
	else \
		echo ".env file already exists."; \
	fi

# Full deployment (setup + build + up)
deploy: setup build up
	@echo "Deployment complete! Check status with 'make status'"

# Development workflow
dev: setup up-build logs

# Production deployment
prod: setup build
	@echo "Built for production. Use 'docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d' to deploy"
