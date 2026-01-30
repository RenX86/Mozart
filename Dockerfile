# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (FFmpeg is required for music)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create the data/downloads directory
RUN mkdir -p src/data/downloads

# Define environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "run.py"]
