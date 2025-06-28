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

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Install development dependencies for hot reloading
# RUN pip install --no-cache-dir watchdog

# # Copy the rest of the application
# COPY . .

# # Set environment variables
# ENV FLASK_APP=run.py
# ENV FLASK_ENV=production
# ENV FLASK_DEBUG=0
# ENV PYTHONPATH=/app

# # Expose port
# EXPOSE 5000

# # Run the application with hot reloading
# CMD ["python", "-u", "run.py"] 


FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies for hot reloading
RUN pip install --no-cache-dir watchdog

# Copy the rest of the application
COPY . .

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Run the application with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "run:app"] 