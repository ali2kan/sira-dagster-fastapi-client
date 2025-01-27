# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Add health check endpoint to the service
COPY healthcheck.py .

# Expose the FastAPI port
EXPOSE 8000

# Command to run the service
CMD ["uvicorn", "trigger_service:app", "--host", "0.0.0.0", "--port", "8000"]
