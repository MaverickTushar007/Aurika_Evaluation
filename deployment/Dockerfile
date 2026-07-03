# deployment/Dockerfile
FROM python:3.10-slim

# Install system dependencies for OpenCV and building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement files first for cache efficiency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source directories
COPY configs/ ./configs/
COPY detection/ ./detection/
COPY tracking/ ./tracking/
COPY semantic/ ./semantic/
COPY counting/ ./counting/
COPY utils/ ./utils/
COPY monitoring/ ./monitoring/
COPY byte_tracker.py .

# Expose API port if deploying as service
EXPOSE 8000

# Set Python Path
ENV PYTHONPATH=/app

CMD ["python", "-m", "detection.yolo_detector"]
