# Multi-stage Dockerfile for Image Processing Pipeline
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    gfortran \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create models directory
RUN mkdir -p /app/models

# Copy model files (if they exist in the build context)
# Create a script to handle optional model file copying
RUN echo '#!/bin/bash\n\
if [ -f "Car Face Blur Model.pt" ]; then\n\
    echo "Copying Car Face Blur Model.pt to models/"\n\
    cp "Car Face Blur Model.pt" /app/models/\n\
else\n\
    echo "Car Face Blur Model.pt not found - will be loaded at runtime"\n\
fi\n\
if [ -f "Car Face Blur Yolov8m.pt" ]; then\n\
    echo "Copying Car Face Blur Yolov8m.pt to models/"\n\
    cp "Car Face Blur Yolov8m.pt" /app/models/\n\
else\n\
    echo "Car Face Blur Yolov8m.pt not found - will be loaded at runtime"\n\
fi' > /app/copy_models.sh && chmod +x /app/copy_models.sh

# Run the model copying script
RUN /app/copy_models.sh || true

# Set permissions
RUN chmod +x /app/start.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "api_server.py"] 