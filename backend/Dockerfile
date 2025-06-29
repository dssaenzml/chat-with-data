FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy pyproject.toml first for better caching
COPY pyproject.toml .

# Copy application code (needed for pyproject.toml installation)
COPY . .

# Install dependencies using uv (much faster than pip)
RUN uv pip install --system --no-cache .

# Create necessary directories
RUN mkdir -p uploads databases logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 