# Stage 1: Builder
FROM python:3.11-alpine as builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    libsodium-dev

COPY requirements.txt .

# Install dependencies into a temporary location
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-alpine

WORKDIR /app

# Install runtime dependencies
# ffmpeg: Required for music playback
# libsodium: Required for PyNaCl (Discord voice support)
# opus: Audio codec
RUN apk add --no-cache \
    ffmpeg \
    libsodium \
    opus \
    ca-certificates

# Copy installed python dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create the data/downloads directory
RUN mkdir -p src/data/downloads

# Define environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "run.py"]
