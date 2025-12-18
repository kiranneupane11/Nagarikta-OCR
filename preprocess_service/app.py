# preprocess_service/app.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import uvicorn
import shutil, os, uuid
import httpx

from model_inference import detect_card
from preprocessing import preprocess_pipeline
from face_detector import face_detector
from config import OCR_SERVICE_URL, OCR_CALL_TIMEOUT, SHARED_DATA_PATH

app = FastAPI()

DATA_DIR = SHARED_DATA_PATH
os.makedirs(DATA_DIR, exist_ok=True)


@app.post("/preprocess")
async def preprocess_image(file: UploadFile = File(...)):
    # 1) save upload
    uid = uuid.uuid4().hex
    ext = os.path.splitext(file.filename)[1] or ".png"
    raw_path = os.path.join(DATA_DIR, f"{uid}_raw{ext}")
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 2) load with cv2
    img = cv2.imread(raw_path)
    (img_height, img_width) = img.shape[:2]
    max_width = 640

    if img_width < max_width:
        raise HTTPException(status_code = 422, detail="Low Image quality. Try with higher resolution image.")

    if img is None:
        raise HTTPException(status_code=400, detail="Could not read uploaded image")

    # 3) detect and crop (detect_card should accept ndarray or path and return ndarray)
    try:
        cropped = detect_card(img, image_path=raw_path)
        if cropped is None:
            raise HTTPException(status_code=404, detail="No ID card detected")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {e}")

    # 4) preprocess pipeline (returns uint8 ndarray)
    try:
        processed = preprocess_pipeline(cropped)  # must be contiguous uint8 
        processed = np.ascontiguousarray(processed, dtype=np.uint8)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preprocessing error: {e}")
    
    #5) Face-Detection
    detected_side = face_detector(processed)
    print(f"Card is: {detected_side} facing.")

    # 6) save processed image
    proc_path = os.path.join(DATA_DIR, f"{uid}_proc.png")
    ok = cv2.imwrite(proc_path, processed)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Failed to write processed file: {proc_path}")

    # 7) Call OCR microservice (which in turn calls LLM) and return final JSON
    try:
        async with httpx.AsyncClient(timeout=OCR_CALL_TIMEOUT) as client:
            resp = await client.post(OCR_SERVICE_URL, json={"image_path": proc_path,"card_side":detected_side})
            resp.raise_for_status()
            final_json = resp.json()
    except httpx.HTTPStatusError as e:
        # downstream returned non-200
        detail = f"OCR service returned {e.response.status_code}: {e.response.text}"
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        # network error, timeout, etc.
        raise HTTPException(status_code=502, detail=f"OCR/LLM call failed: {type(e).__name__}: {e}")

    # Return both paths for debugging plus the final structured JSON the LLM produced
    return JSONResponse({"raw_path": raw_path, "processed_path": proc_path, "result": final_json})

@app.get("/health")
def health():
    """Health check endpoint for Docker"""
    return {"status": "running", "service": "preprocess_service"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
