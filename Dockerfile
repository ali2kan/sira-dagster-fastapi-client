# Use Python 3.9 image
FROM python:3.9

# Set working directory
WORKDIR /code

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY trigger_service /code/trigger_service

# Command to run the application
CMD ["uvicorn", "trigger_service.trigger:app", "--host", "0.0.0.0", "--port", "8000"]

