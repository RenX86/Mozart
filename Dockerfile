# Stage 1: Builder
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies
# rust and cargo are required for the 'davey' package (maturin-based)
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    libsodium-dev \
    rust \
    cargo \
    openssl-dev

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
# openssl: Required for davey (E2EE/DAVE protocol)
RUN apk add --no-cache \
    ffmpeg \
    libsodium \
    opus \
    openssl \
    ca-certificates

# Copy installed python dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create the data/downloads directory
RUN mkdir -p src/data/downloads

# Define environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 5000

# Run the application
CMD ["python", "run.py"]
