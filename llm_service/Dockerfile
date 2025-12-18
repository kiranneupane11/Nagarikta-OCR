# llm_service/Dockerfile.lightweight

# ============== BUILD STAGE ==============
FROM python:3.10-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Lightweight requirements 
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    requests \
    pydantic \
    "thefuzz[speedup]" \
    python-levenshtein \
    instructor \
    httpx \
    openai

# ============== RUNTIME STAGE ==============
FROM python:3.10-slim AS runtime

LABEL maintainer="micro-ocr"
LABEL service="llm_service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY app.py config.py post_processing.py prompts.py schema.py ./

RUN mkdir -p /app/shared_data

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]