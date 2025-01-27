# Use Python 3.9 image
FROM python:3.12-slim

# Set working directory
WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*



COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# COPY trigger_service /code/trigger_service

COPY . .

