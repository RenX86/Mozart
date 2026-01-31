# Use Alpine Linux for a much smaller image size
FROM python:3.11-alpine

# Set the working directory
WORKDIR /app

# Install system dependencies using apk (Alpine Package Keeper)
# ffmpeg: Required for music playback
# git: Useful for yt-dlp updates
# libsodium-dev: Required for PyNaCl (Discord voice support)
# build-base, libffi-dev: Required to compile Python C-extensions
RUN apk add --no-cache \
    ffmpeg \
    git \
    libsodium-dev \
    build-base \
    libffi-dev

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# This compiles pynacl and others which is why we needed build-base
RUN pip install --no-cache-dir -r requirements.txt

# OPTIONAL: Remove build dependencies to save even more space
# We keep libsodium-dev as it might be needed at runtime depending on linking
# RUN apk del build-base libffi-dev

# Copy the rest of the application
COPY . .

# Create the data/downloads directory
RUN mkdir -p src/data/downloads

# Define environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "run.py"]
