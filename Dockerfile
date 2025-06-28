# FROM python:3.9-slim

# # Set working directory
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements first to leverage Docker cache
# COPY requirements.txt .



# # Create directory structure
# RUN mkdir -p /app/app
# # Verify file will be available
# RUN ls -la /app/app || echo "Directory will be mounted"
# # Install Python dependencies
# RUN pip install --no-cache-dir --default-timeout=100  -r requirements.txt

# # Install development dependencies for hot reloading
# RUN pip install --no-cache-dir watchdog

# # Copy the rest of the application
# COPY . .

# # Set environment variables
# ENV FLASK_APP=run.py
# ENV FLASK_ENV=development
# ENV FLASK_DEBUG=1
# ENV PYTHONPATH=/app

# # Expose port
# EXPOSE 5000

# # Run the application with hot reloading
# CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--reload"] 

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt tiktoken flask_wtf

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]