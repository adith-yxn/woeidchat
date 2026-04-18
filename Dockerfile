FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn

# Create necessary directories (uploads is runtime-created)
RUN mkdir -p woeidchat_keys uploads

# Copy application and assets
COPY woeidchat_premium_server.py .
COPY static/ ./static/

# Expose port (Fly.io will use PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server with proper PORT handling
CMD ["python", "-u", "woeidchat_premium_server.py"]
