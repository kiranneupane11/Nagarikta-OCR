# llm_service/app.py
import asyncio
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

import instructor
from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, DATA_DIR
from post_processing import NepalAddressValidator
from prompts import FRONT_PROMPT, BACK_PROMPT
from schema import FrontSideCard, BackSideCard

app = FastAPI(title="LLM Extraction Service (Ollama + Instructor)")

SHARED_DATA_DIR = DATA_DIR
os.makedirs(SHARED_DATA_DIR, exist_ok=True)

# Global executor for non-blocking I/O and processing
executor = ThreadPoolExecutor(max_workers=4)

# Initialize Validator once
validator = NepalAddressValidator()

# Ensure `ollama run gemma2:2b` is running in your terminal/background.
client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)

# Patch OpenAI client with Instructor for structured output
patched_client = instructor.from_openai(client, mode=instructor.Mode.JSON_SCHEMA)

def llm_extract(text: str, side:str) -> Dict[str, Any]:
    """
    Sends text to Ollama (gemma2:2b) via Instructor to get structured JSON.
    """    
    if side == "front":
        response_model = FrontSideCard
        system_content = FRONT_PROMPT
    else:
        # Default to front if unknown
        response_model = BackSideCard
        system_content = BACK_PROMPT

    try:
        # Instructor handles the heavy lifting of validation and retries
        result = patched_client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"""Extract all information from this Nepali Citizenship Card OCR text.
                Text:
                {text}

                Return only valid JSON matching the exact schema. No explanations, no markdown, no extra text."""}
            ],
            response_model=response_model,
            temperature=0.0,
            max_tokens=500,
        )
        return result.model_dump()

    except Exception as e:
        print(f"Extraction failed: {e}")
        # Return empty model on failure to prevent API 500 errors
        return response_model().model_dump()


def post_process_result(raw_llm: dict, side: str ) -> dict:
    """Wrapper to run validation safely."""
    try:
        return validator.post_process(raw_llm, side)
    except Exception as e:
        return {"error": "post-process failed", "details": str(e), "raw": raw_llm}


class ExtractInput(BaseModel):
    text: str
    card_side: str = "unknown"

@app.post("/extract")
async def extract_data(input: ExtractInput) -> Dict:
    loop = asyncio.get_running_loop()
    
    # 1. Detect side 
    side = input.card_side
    
    # 2. Setup Debugging
    request_id = uuid.uuid4().hex[:12]
    debug_file = f"extract_{request_id}.txt"
    debug_path = os.path.join(SHARED_DATA_DIR, debug_file)

    try:
        # 3. Run LLM Extraction (CPU/Network bound, so run in executor)
        raw_json = await asyncio.wait_for(
            loop.run_in_executor(executor, llm_extract, input.text, side),
            timeout=120, # Timeout if Ollama hangs
        )

        # 4. Save Raw Output for Debugging
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write("=== LLM OUTPUT ===\n")
            f.write(json.dumps(raw_json, indent=2, ensure_ascii=False))

        # 5. Post-Process (Address cleaning, normalization)
        result = await loop.run_in_executor(executor, post_process_result, raw_json, side)

        # 6. Attach Metadata
        result["metadata"] = {
            "request_id": request_id,
            "detected_card_side": side,
            "extraction_method": f"Instructor+Ollama({OLLAMA_MODEL})",
            "debug_file": debug_file,
        }
        return result

    except asyncio.TimeoutError:
        return {"error": "Timeout after 120s - Is Ollama running?", "debug_file": debug_file}
    except Exception as e:
        return {"error": "Unexpected error", "details": str(e), "debug_file": debug_file}

@app.get("/health")
def health():
    return {"status": "running", "backend": "ollama", "model": OLLAMA_MODEL}


if __name__ == "__main__":
    import uvicorn
    # Run simple server
    uvicorn.run(app, host="0.0.0.0", port=8001)