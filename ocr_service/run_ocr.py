# ocr_service/run_ocr.py
import cv2
import numpy as np
import pytesseract
from typing import Tuple, Optional
import re

_PADDLE_OCR: Optional[object] = None
_PADDLE_OCR_ERROR: Optional[str] = None

def _init_paddleocr():
    """
    Initialize PaddleOCR instance at module load time.
    Called once when the module is imported.
    """
    global _PADDLE_OCR, _PADDLE_OCR_ERROR
    
    if _PADDLE_OCR is not None:
        return _PADDLE_OCR
    
    try:
        print("Initializing PaddleOCR...")
        
        from paddleocr import PaddleOCR
        
        _PADDLE_OCR = PaddleOCR(
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True,
            lang="ne"
        )
        
        print("PaddleOCR initialized successfully!")
        return _PADDLE_OCR
        
    except Exception as e:
        _PADDLE_OCR_ERROR = str(e)
        print(f"PaddleOCR initialization failed: {e}")
        return None


def get_paddleocr():
    """
    Get the PaddleOCR instance.
    Returns None if initialization failed.
    """
    global _PADDLE_OCR
    if _PADDLE_OCR is None and _PADDLE_OCR_ERROR is None:
        _init_paddleocr()
    return _PADDLE_OCR


def is_paddleocr_available() -> bool:
    """
    Check if PaddleOCR is available and initialized.
    """
    return get_paddleocr() is not None


# Initialize PaddleOCR when module is loaded
_init_paddleocr()


def _is_valid_ocr_result(text: str, min_length: int = 10, min_alpha_ratio: float = 0.3) -> bool:
    """
    Check if OCR result is valid and not garbage.
    
    Args:
        text: OCR output text
        min_length: Minimum character length to be considered valid
        min_alpha_ratio: Minimum ratio of alphanumeric/Devanagari characters
    
    Returns:
        True if text appears valid, False if empty or garbage
    """
    if not text:
        return False
    
    # Remove whitespace for analysis
    cleaned = text.strip()
    
    # Check if empty or too short
    if len(cleaned) < min_length:
        print(f"  ⚠ Text too short: {len(cleaned)} chars (min: {min_length})")
        return False
    
    # Count meaningful characters (alphanumeric + Devanagari Unicode range)
    # Devanagari range: \u0900-\u097F
    meaningful_chars = len(re.findall(r'[\w\u0900-\u097F]', cleaned))
    total_chars = len(cleaned.replace(' ', '').replace('\n', ''))
    
    if total_chars == 0:
        return False
    
    alpha_ratio = meaningful_chars / total_chars
    
    if alpha_ratio < min_alpha_ratio:
        print(f"  ⚠ Low meaningful char ratio: {alpha_ratio:.2f} (min: {min_alpha_ratio})")
        return False
    
    # Check for repetitive garbage patterns
    if re.match(r'^(.)\1{5,}$', cleaned.replace(' ', '').replace('\n', '')):
        print("Detected repetitive garbage pattern")
        return False
    
    return True


def _try_paddleocr(image):
    """
    Try PaddleOCR for text extraction.
    """
    ocr = get_paddleocr()
    
    if ocr is None:
        raise RuntimeError(f"PaddleOCR not available: {_PADDLE_OCR_ERROR or 'Unknown error'}")
    
    try:
        # Paddle expects numpy array
        result = ocr.predict(image)
        text_lines = []
        for res in result:
            if isinstance(res, dict) and 'rec_texts' in res:
                text_lines.extend(res['rec_texts'])
        text = "\n".join(text_lines) if text_lines else "No text found"
        return text
    except Exception as e:
        # bubble up to caller to allow fallback
        raise


def _detect_orientation(image):
    """
    Detect image orientation using Tesseract OSD (Orientation and Script Detection).
    Returns orientation info dict or None if detection fails.
    """
    try:
        osd_output = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
        return {
            "orientation": osd_output.get("orientation", 0),
            "orientation_conf": osd_output.get("orientation_conf", 0),
            "rotate": osd_output.get("rotate", 0),
            "script": osd_output.get("script", "Unknown"),
            "script_conf": osd_output.get("script_conf", 0)
        }
    except pytesseract.TesseractError as e:
        print(f"⚠ Orientation detection failed: {e}")
        return None


def _rotate_image(image, angle):
    """
    Rotate image by the given angle (0, 90, 180, 270).
    """
    if angle == 0:
        return image
    elif angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    else:
        return image


def _run_tesseract(image):
    """
    Fallback OCR using Tesseract with orientation detection.
    """
    print("Using Tesseract OCR with orientation detection...")
    
    # Detect orientation
    orientation_info = _detect_orientation(image)
    
    # Rotate image if needed
    if orientation_info and orientation_info["rotate"] != 0:
        rotation_angle = orientation_info["rotate"]
        print(f"↻ Rotating image by {rotation_angle}° to correct orientation")
        image = _rotate_image(image, rotation_angle)
    
    if orientation_info:
        print(f"  Detected script: {orientation_info['script']}")
        print(f"  Orientation: {orientation_info['orientation']}°")
    
    # Run Tesseract OCR
    text = pytesseract.image_to_string(image, lang='nep')
    
    return text


def run_ocr_for_path(image_path: str, card_side: str = "front") -> Tuple[str, str]:
    """
    OCR pipeline with PaddleOCR as primary engine.
    Tesseract is used only as a fallback if PaddleOCR fails or returns garbage.
    """

    print(f"OCR Processing: {image_path}")
    print(f"Card Side: {card_side}")

    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Cannot load image: {image_path}")

    image = np.ascontiguousarray(img, dtype=np.uint8)

    # ---------------- Primary OCR: PaddleOCR ----------------
    try:
        print("→ Using PaddleOCR")
        text = _try_paddleocr(image)
        engine = "PaddleOCR"

        if _is_valid_ocr_result(text, card_side):
            return _finalize(text, engine)

        print("PaddleOCR returned low-quality output")

    except Exception as e:
        print(f"PaddleOCR failed: {e}")

    # ---------------- Fallback OCR: Tesseract ----------------
    try:
        print("Falling back to Tesseract")
        fallback_text = _run_tesseract(image)
        fallback_engine = "Tesseract (fallback)"

        if _is_valid_ocr_result(fallback_text, card_side):
            return _finalize(fallback_text, fallback_engine)

        print("Tesseract also returned low-quality output")

    except Exception as e:
        print(f"Tesseract failed: {e}")

    # ---------------- Best-effort return ----------------
    print(" Returning PaddleOCR output")
    return _finalize(text if 'text' in locals() else "", "PaddleOCR")


def _finalize(text: str, engine: str) -> Tuple[str, str]:
    print(f"OCR completed using {engine}")
    print(f"Text length: {len(text)} characters")
    return text, engine
