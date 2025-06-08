# Multi-stage Dockerfile for Prism DNS Server (SCRUM-12)

# Development stage
FROM python:3.11-slim as development

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy server requirements first for better layer caching
COPY server/requirements.txt /app/server/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy application code
COPY . /app/

# Create non-root user for security
RUN groupadd -r prism && useradd -r -g prism prism
RUN chown -R prism:prism /app

# Expose ports for TCP server and REST API
EXPOSE 8080 8081

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER prism

# Default command for development
CMD ["python", "-m", "server.main"]

# Production stage
FROM development as production

# Copy only necessary files for production
COPY --from=development /app/server /app/server
COPY --from=development /app/config /app/config

# Use production configuration
ENV PRISM_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/api/health || exit 1

# Production command
CMD ["uvicorn", "server.api.app:app", "--host", "0.0.0.0", "--port", "8081"]

# Test stage
FROM python:3.11-slim as test

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy server requirements first for better layer caching
COPY server/requirements.txt /app/server/requirements.txt

# Install Python dependencies (including test dependencies)
RUN pip install --no-cache-dir -r server/requirements.txt
RUN pip install --no-cache-dir coverage pytest-cov

# Copy application code
COPY . /app/

# Create non-root user for security
RUN groupadd -r prism && useradd -r -g prism prism
RUN chown -R prism:prism /app
USER prism

# Set test environment
ENV PRISM_ENV=test
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command for testing
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=server"]