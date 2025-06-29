FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy pyproject.toml first for better caching
COPY pyproject.toml .

# Copy application code (needed for pyproject.toml installation)
COPY . .

# Install dependencies using uv (much faster than pip)
RUN uv pip install --system --no-cache .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the application
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"] 