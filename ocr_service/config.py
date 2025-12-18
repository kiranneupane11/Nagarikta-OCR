from pathlib import Path
import os

# Shared data path (from environment or default)
SHARED_DATA_PATH = os.getenv("SHARED_DATA_PATH", "/app/shared_data")

# For local development fallback
if not os.path.exists(SHARED_DATA_PATH) and os.path.exists("../shared_data"):
    SHARED_DATA_PATH = os.path.abspath("../shared_data")

# Ensure directory exists
os.makedirs(SHARED_DATA_PATH, exist_ok=True)

# OCR Text output path
OCR_TEXT_PATH = Path(SHARED_DATA_PATH)

# LLM Service URL (Docker service name)
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001/extract")

print(f"[CONFIG] SHARED_DATA_PATH: {SHARED_DATA_PATH}")
print(f"[CONFIG] LLM_SERVICE_URL: {LLM_SERVICE_URL}")