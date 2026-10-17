# ==============================================================================
# Production Dockerfile for Gig-Aid
# Optimized for Google Cloud Run (Non-root user, dynamic $PORT binding)
# ==============================================================================

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create a non-root user for security
RUN useradd -u 10001 -m appuser && \
    chown -R appuser:appuser /app

USER appuser

# Cloud Run injects $PORT environment variable (default: 8080)
EXPOSE 8080

# Run uvicorn server binding dynamically to $PORT
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
