FROM python:3.9-slim

LABEL maintainer="Smart NOC Team"
LABEL description="Device Enrichment Service - Provides device metadata for log enrichment"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=3)"

# Run application
CMD ["python", "app.py"]
