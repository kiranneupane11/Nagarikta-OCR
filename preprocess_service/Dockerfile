# ============== BUILD STAGE ==============
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy and install all requirements + TensorFlow in one command for proper dependency resolution
COPY requirements.txt .
RUN pip install --no-cache-dir \
    "tensorflow-cpu==2.19.0" \
    -r requirements.txt

# SAFE cleanup - only remove obvious cache files, NOT package internals
RUN find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -name "*.pyc" -delete 2>/dev/null || true && \
    find /opt/venv -name "*.pyo" -delete 2>/dev/null || true && \
    rm -rf /root/.cache/pip

# ============== RUNTIME STAGE ==============
FROM python:3.10-slim AS runtime

LABEL maintainer="micro-ocr"
LABEL service="preprocess_service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    TF_CPP_MIN_LOG_LEVEL=2

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy only needed application files
COPY app.py config.py face_detector.py model_inference.py preprocessing.py ./

# Create directories
RUN mkdir -p /app/shared_data /app/models

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]