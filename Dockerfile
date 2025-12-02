# Bio-Systems Engineering - Reproducible Environment
# Python 3.11 slim image for minimal size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for scientific packages)
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package source
COPY src/ ./src/
COPY pyproject.toml .

# Install package in editable mode
RUN pip install --no-cache-dir -e .

# Copy data and reports (if needed)
# Note: data/raw/ is .gitignored and should be mounted as volume
COPY data/processed/ ./data/processed/
COPY reports/ ./reports/
COPY notebooks/ ./notebooks/

# Create directory for output
RUN mkdir -p /app/output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command: Run tests
CMD ["pytest", "--verbose"]

# Usage examples:
# 
# Build:
#   docker build -t biosystems:1.0.0 .
#
# Run tests:
#   docker run biosystems:1.0.0
#
# Run analysis with data volume:
#   docker run -v $(pwd)/data/raw:/app/data/raw biosystems:1.0.0 python scripts/analyze.py
#
# Interactive shell:
#   docker run -it biosystems:1.0.0 /bin/bash
#
# Run Jupyter (expose port 8888):
#   docker run -p 8888:8888 biosystems:1.0.0 jupyter notebook --ip=0.0.0.0 --allow-root
