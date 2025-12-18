import os
from pathlib import Path

# Shared data path
SHARED_DATA_PATH = os.getenv("SHARED_DATA_PATH", "/app/shared_data")

# Models path
MODELS_PATH = os.getenv("MODELS_PATH", "/app/models")

# For local development fallback
if not os.path.exists(SHARED_DATA_PATH) and os.path.exists("../shared_data"):
    SHARED_DATA_PATH = os.path.abspath("../shared_data")

if not os.path.exists(MODELS_PATH) and os.path.exists("../models"):
    MODELS_PATH = os.path.abspath("../models")

# Ensure directories exist
os.makedirs(SHARED_DATA_PATH, exist_ok=True)

# Output path for cropped images
CROPPED_OUTPUT_PATH = Path(SHARED_DATA_PATH)

# Model paths
MODEL_DIR = Path(MODELS_PATH)
PATH_TO_MODEL = str(MODEL_DIR)
PATH_TO_LABELS = str(MODEL_DIR / "labelmap.pbtxt")

# Inference settings
MIN_SCORE = 0.6
MIN_RESOLUTION = 640

# OCR Service URL (Docker service name)
OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://localhost:9000/ocr")

# Timeout for OCR -> LLM pipeline
OCR_CALL_TIMEOUT = 300

print(f"[CONFIG] SHARED_DATA_PATH: {SHARED_DATA_PATH}")
print(f"[CONFIG] MODELS_PATH: {MODELS_PATH}")
print(f"[CONFIG] OCR_SERVICE_URL: {OCR_SERVICE_URL}")