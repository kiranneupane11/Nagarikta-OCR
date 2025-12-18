import os

# Ollama Configuration (Docker-aware)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/v1"

# Shared Data Directory
DATA_DIR = os.getenv("DATA_PATH", "/app/shared_data")

# Fallback for local development
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "shared_data")

# Ensure directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Location in Nepali
MUNI_JSON = os.path.join(DATA_DIR, "nepal_municipalities_by_district.json")
VDC_JSON = os.path.join(DATA_DIR, "nepal_vdcs_by_district.json")

# Location in English
EN_MUNI_JSON = os.path.join(DATA_DIR, "en_nepal_municipalities_by_district.json")
EN_VDC_JSON = os.path.join(DATA_DIR, "en_nepal_vdcs_by_district.json")