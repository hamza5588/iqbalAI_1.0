FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better cache utilization
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies for hot reloading
RUN pip install --no-cache-dir watchdog

# Copy the rest of the application
COPY . .

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_DEBUG=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Command to run the application with hot reloading
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--reload"] 