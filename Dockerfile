FROM python:3.10-slim

# Install system dependencies
# - poppler-utils: for pdf2image thumbnail generation
# - tesseract-ocr: lightweight OCR engine fallback
# - libpq-dev/gcc: for potential C-extensions if needed
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install CPU-only PyTorch (Crucial for staying within sensible image sizes)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations and start the server
# Using migrate.py as it is the current database management script
CMD ["sh", "-c", "python migrate.py upgrade && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
