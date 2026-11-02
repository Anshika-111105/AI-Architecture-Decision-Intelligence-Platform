# Use Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --default-timeout=300 --retries=10 -r requirements.txt

# Copy ML project
COPY ml/ ./ml/

# Set Python path
ENV PYTHONPATH=/app

# Run ML tests
CMD ["python", "-m", "pytest", "ml/tests", "-v"]