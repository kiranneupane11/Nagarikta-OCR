# ocr_service/Dockerfile

# ============== BUILD STAGE ==============
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt .

# Install PaddlePaddle (CPU version)
RUN pip install --no-cache-dir paddlepaddle

# Install PaddleOCR
RUN pip install --no-cache-dir paddleocr

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create model cache directories (in case they don't exist)
RUN mkdir -p /root/.paddlex /root/.paddleocr

# Pre-download PaddleOCR models during build
RUN python -c "\
from paddleocr import PaddleOCR;\
print('Downloading PaddleOCR models...');\
ocr = PaddleOCR(\
    use_doc_orientation_classify=True,\
    use_doc_unwarping=True,\
    use_textline_orientation=True,\
    lang='ne'\
);\
print('PaddleOCR models downloaded successfully!');\
"

# Safe cleanup - only pycache, NOT package internals
RUN find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -name "*.pyc" -delete 2>/dev/null || true && \
    find /opt/venv -name "*.pyo" -delete 2>/dev/null || true && \
    rm -rf /root/.cache/pip

# ============== RUNTIME STAGE ==============
FROM python:3.10-slim AS runtime

LABEL maintainer="micro-ocr"
LABEL service="ocr_service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DISABLE_MODEL_SOURCE_CHECK=True

WORKDIR /app

# Install ONLY runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-nep \
    tesseract-ocr-osd \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy PaddleX model cache from builder (this is where models are stored)
COPY --from=builder /root/.paddlex /root/.paddlex

# Copy .paddleocr if it exists (may be empty)
COPY --from=builder /root/.paddleocr /root/.paddleocr

# Copy only needed application files
COPY app.py config.py run_ocr.py ./

# Create shared_data directory
RUN mkdir -p /app/shared_data

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=5 \
    CMD curl -f http://localhost:9000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]