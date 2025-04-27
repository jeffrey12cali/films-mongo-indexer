# Use official Python Alpine image for minimal footprint
FROM python:3.11-alpine

# Unbuffered stdout and stderr (so logs appear immediately)
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /films-mongo-indexer

# Install system dependencies for building certain Python packages
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    ca-certificates

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY indexer.py .

# Set default MOVIES_PATH and designate it as a volume
ENV MOVIES_PATH=/movies
VOLUME ["/movies"]

# Default command
CMD ["python", "-u", "indexer.py"]

