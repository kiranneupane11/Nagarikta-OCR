# ocr_service/app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import httpx
from datetime import datetime
from pydantic import BaseModel

from pathlib import Path
from config import OCR_TEXT_PATH, LLM_SERVICE_URL
from run_ocr import run_ocr_for_path


app = FastAPI()

class OCRInput(BaseModel):
    image_path: str
    card_side: str

def check_ocr_text_file(file_path: Path) -> bool:
    """Check if the OCR text in the file is valid (not empty or too short)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Split after the header
        parts = content.split("\n\n", 1)
        if len(parts) < 2:
            return False
        text_part = parts[1].strip()
        if not text_part or len(text_part) < 10: 
            return False
        return True
    except Exception as e:
        print(f"Warning: Failed to check OCR text file: {e}")
        return False

def save_ocr_text(text: str, image_path: str, card_side: str, engine: str):
    """Save raw OCR output to a text file with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  
    image_name = Path(image_path).stem

    filename = f"OCR-output_{timestamp}_{image_name}.txt"
    file_path = OCR_TEXT_PATH / filename

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("=== RAW OCR OUTPUT ===\n")
            f.write(f"Image: {image_path}\n")
            f.write(f"Card Side: {card_side}\n")
            f.write(f"OCR Engine: {engine}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("="*50 + "\n\n")
            f.write(text.strip())
        print(f"OCR text saved → {file_path}")
    except Exception as e:
        print(f"Warning: Failed to save OCR text: {e}")


@app.post("/ocr")
async def ocr_entry(input_data: OCRInput):
    """
    Expects:
    {
        "image_path": "/absolute/path/to/cropped_image.png"
    }
    
    Output:
        Final JSON from LLM service
    """

    image_path = Path(input_data.image_path)
    card_side = input_data.card_side

    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image does not exist: {image_path}")

    # --- 1. Run OCR ---
    try:
        ocr_text, engine_used = run_ocr_for_path(str(image_path), card_side)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")
    
    saved_path = save_ocr_text(ocr_text, str(image_path), card_side, engine_used)

    # --- 2. Send OCR text to LLM Microservice ---
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            llm_response = await client.post(
                LLM_SERVICE_URL,
                json={"text": ocr_text, "card_side": card_side}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed connecting to LLM service: {e}")
    

    if llm_response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"LLM service error: {llm_response.text}"
        )

    final_json = llm_response.json()

    if "metadata" not in final_json:
        final_json["metadata"] = {}
    
    final_json["metadata"]["ocr_engine"] = engine_used
    final_json["metadata"]["card_side"] = card_side
    if saved_path:
        final_json["metadata"]["ocr_output_file"] = saved_path

    return JSONResponse(final_json)

@app.get("/health")
def health():
    """Health check endpoint for Docker"""
    return {"status": "running", "service": "ocr_service"}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=9000,
        reload=True
    )