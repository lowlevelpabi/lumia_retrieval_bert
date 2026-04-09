# ── Build Stage ──────────────────────────────────────────────────────────────
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a virtualenv to stay isolated and easy to copy
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# 1. Install CPU-only PyTorch first (Essential for staying under 4GB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 3. Strip unnecessary files from the virtualenv to save space
RUN find /opt/venv -type d -name "__pycache__" -exec rm -rf {} +

# ── Runtime Stage ────────────────────────────────────────────────────────────
FROM python:3.10-slim

# Install runtime-only system dependencies
# - poppler-utils: for pdf2image
# - libpq5: for postgres (psycopg2)
# - tesseract-ocr: lightweight OCR fallback instead of EasyOCR
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libpq5 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtualenv from the builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the application code
# (Ensure .dockerignore skips venv, .git, qdrant_storage, etc.)
COPY . .

# Use shell form to expand environment variables and run migrations
# Using the venv's python/uvicorn
CMD ["sh", "-c", "python migrate.py upgrade && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
