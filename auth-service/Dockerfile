# ---- Go Builder Stage ----
FROM golang:1.24.3 AS builder

WORKDIR /app/auth-service

# Copy Go module files
COPY go.mod ./go.mod
COPY go.sum ./go.sum
RUN go mod download

# Copy the rest of the Go application source
COPY . ./

# Build the Go application as a static binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o auth-service-server ./cmd/api

# ---- Final Stage ----
FROM debian:12-slim AS final

WORKDIR /app

# Copy the built Go executable from the builder stage
COPY --from=builder /app/auth-service/auth-service-server /app/auth-service-server

# Copy test files and runner script
COPY --from=builder /app/auth-service/tests /app/tests
COPY --from=builder /app/auth-service/requirements.txt /app/requirements.txt
COPY --from=builder /app/auth-service/run_tests.sh /app/run_tests.sh

# Ensure the executables are runnable
RUN chmod +x /app/auth-service-server
RUN chmod +x /app/run_tests.sh

# Install CA certificates for TLS and Python dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python test dependencies
RUN pip3 install --break-system-packages -r /app/requirements.txt

# Expose port
EXPOSE 8081