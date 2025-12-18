# model_inference.py
import os
import cv2
import tensorflow as tf
import numpy as np
from PIL import Image as PILImage
from pathlib import Path

from config import PATH_TO_MODEL, PATH_TO_LABELS, MIN_SCORE, CROPPED_OUTPUT_PATH

# Module-level caches so the model is loaded only once.
_DETECT_FN = None
_CATEGORY_INDEX = None

def parse_labelmap(labelmap_path=PATH_TO_LABELS):
    """
    Parses a simple pbtxt-style labelmap (fallbacks to {1: 'object'}).
    """
    classes = {}
    try:
        if not labelmap_path or not os.path.exists(labelmap_path):
            return {1: {'id': 1, 'name': 'object'}}
        with open(labelmap_path, 'r', encoding='utf-8') as f:
            current_id = None
            current_name = None
            for line in f:
                line = line.strip()
                if line.startswith('id:'):
                    try:
                        current_id = int(line.split(':', 1)[1].strip())
                    except:
                        current_id = None
                elif line.startswith('display_name:') or line.startswith('name:'):
                    current_name = line.split(':', 1)[1].strip().strip('"').strip("'")
                elif line == '}' and current_id is not None and current_name:
                    classes[current_id] = {'id': current_id, 'name': current_name}
                    current_id, current_name = None, None
        return classes if classes else {1: {'id': 1, 'name': 'object'}}
    except Exception:
        return {1: {'id': 1, 'name': 'object'}}


def load_model(model_path=PATH_TO_MODEL):
    """
    Load the TF SavedModel and cache the signature. Raises RuntimeError if loading fails.
    """
    global _DETECT_FN
    if _DETECT_FN is not None:
        return _DETECT_FN

    if not model_path or not os.path.exists(model_path):
        raise RuntimeError(f"SavedModel path not found: {model_path}")

    try:
        detect_module = tf.saved_model.load(model_path)
        # prefer serving_default if present
        if hasattr(detect_module, "signatures") and detect_module.signatures:
            detect_fn = detect_module.signatures.get('serving_default', next(iter(detect_module.signatures.values())))
        else:
            # fallback: try calling the module directly (some SavedModels expose call)
            detect_fn = detect_module
        _DETECT_FN = detect_fn
        print("   -> Model loaded successfully.")
        return _DETECT_FN
    except Exception as e:
        raise RuntimeError(f"Could not load SavedModel from {model_path}: {e}")


def load_image(image):
    """
    Accepts either a path (str / Path) or a BGR numpy array and returns (bgr_array, input_tensor).
    input_tensor is uint8 [1,H,W,3] suitable for many TF detection signatures.
    """
    if isinstance(image, (str, Path)):
        img = cv2.imread(str(image))
        if img is None:
            raise ValueError(f"cv2.imread failed to read image: {image}")
    elif isinstance(image, np.ndarray):
        img = image
    else:
        raise TypeError("load_image expects a file path or numpy.ndarray (BGR).")

    # Ensure uint8 BGR
    img = img.astype(np.uint8, copy=False)
    # Create tensor shaped [1, H, W, 3]
    input_tensor = tf.convert_to_tensor(np.expand_dims(img, axis=0), dtype=tf.uint8)
    return img, input_tensor


def run_detection(detect_fn, input_tensor):
    """
    Runs detection using the provided signature function. Attempts to handle common signature names.
    Returns (boxes, scores, classes) as numpy arrays.
    """
    # Handle both signature-callable and dict-like outputs
    try:
        # If detect_fn is a Signature, get its structured_input_signature to find input name
        if hasattr(detect_fn, "structured_input_signature"):
            _, sig_kwargs = detect_fn.structured_input_signature
            if sig_kwargs:
                input_key = list(sig_kwargs.keys())[0]
                outputs = detect_fn(**{input_key: input_tensor})
            else:
                outputs = detect_fn(input_tensor)
        else:
            outputs = detect_fn(input_tensor)
    except Exception as e:
        raise RuntimeError(f"Detection call failed: {e}")

    # Common keys: detection_boxes, detection_scores, detection_classes
    def to_np(key):
        if key in outputs:
            return outputs[key][0].numpy()
        # try alternatives
        for alt in ('boxes', 'detection_box', 'output_boxes'):
            if alt in outputs:
                return outputs[alt][0].numpy()
        return None

    boxes = outputs.get('detection_boxes') if 'detection_boxes' in outputs else outputs.get('boxes')
    scores = outputs.get('detection_scores') if 'detection_scores' in outputs else outputs.get('scores')
    classes = outputs.get('detection_classes') if 'detection_classes' in outputs else outputs.get('classes')

    # Convert to numpy safely
    try:
        boxes_np = boxes[0].numpy() if boxes is not None else None
        scores_np = scores[0].numpy() if scores is not None else None
        classes_np = classes[0].numpy().astype(np.int32) if classes is not None else None
    except Exception:
        # fallback: try other access patterns
        boxes_np = np.array(boxes) if boxes is not None else None
        scores_np = np.array(scores) if scores is not None else None
        classes_np = np.array(classes).astype(np.int32) if classes is not None else None

    return boxes_np, scores_np, classes_np


def get_crop_coordinates(scores, boxes, classes, category_index, min_score):
    """
    Returns normalized box [ymin, xmin, ymax, xmax] for the highest scoring detection,
    or full-image box if none meet threshold.
    """
    if boxes is None or scores is None:
        return [0.0, 0.0, 1.0, 1.0]

    if len(scores) == 0 or np.all(scores < min_score):
        return [0.0, 0.0, 1.0, 1.0]

    best_idx = int(np.argmax(scores))
    if scores[best_idx] < min_score:
        return [0.0, 0.0, 1.0, 1.0]

    ymin, xmin, ymax, xmax = boxes[best_idx].tolist()
    cls_id = int(classes[best_idx]) if classes is not None else 1
    cls_name = category_index.get(cls_id, {'name': 'object'})['name'] if category_index else 'object'
    print(f"   -> Detection Found: {cls_name} ({int(scores[best_idx]*100)}%)")
    return [ymin, xmin, ymax, xmax]


def crop_image(image_cv, ymin, xmin, ymax, xmax):
    """
    Crop and return a PIL.Image (RGB). If coordinates are full image, return a PIL copy of the input.
    """
    im_height, im_width = image_cv.shape[:2]
    left = int(max(0, xmin) * im_width)
    right = int(min(1.0, xmax) * im_width)
    top = int(max(0, ymin) * im_height)
    bottom = int(min(1.0, ymax) * im_height)

    # Protect against degenerate boxes
    if right <= left or bottom <= top:
        # return whole image as PIL
        pil = PILImage.fromarray(cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB))
        return pil

    image_pil = PILImage.fromarray(cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB))
    roi_box = (left, top, right, bottom)
    cropped_im = image_pil.crop(roi_box)
    return cropped_im


def detect_card(image, image_path: str = None):
    """
    Public entrypoint used by preprocess_service.
    Accepts image (ndarray BGR) or path string. Returns cropped BGR numpy array (uint8, contiguous).
    """
    global _DETECT_FN, _CATEGORY_INDEX

    # Load model & category index once
    if _DETECT_FN is None:
        _DETECT_FN = load_model(PATH_TO_MODEL)
    if _CATEGORY_INDEX is None:
        _CATEGORY_INDEX = parse_labelmap(PATH_TO_LABELS)

    # Load image into cv2 BGR and prepare tensor
    img_cv, input_tensor = load_image(image)

    # Run detection
    boxes, scores, classes = run_detection(_DETECT_FN, input_tensor)

    # Get crop coordinates
    ymin, xmin, ymax, xmax = get_crop_coordinates(scores, boxes, classes, _CATEGORY_INDEX, MIN_SCORE)

    # Crop image (returns PIL)
    cropped_pil = crop_image(img_cv, ymin, xmin, ymax, xmax)

    # Ensure output directory exists
    os.makedirs(CROPPED_OUTPUT_PATH, exist_ok=True)
    # Save cropped as PNG (filename derived from image_path if provided)
    if image_path and isinstance(image_path, (str, Path)):
        input_path = Path(image_path)
        out_name = f"{input_path.stem}_cropped{input_path.suffix or '.png'}"
    else:
        out_name = "input-image-cropped.png"
    output_file = os.path.join(CROPPED_OUTPUT_PATH, out_name)
    cropped_pil.save(output_file, format='PNG')
    print(f"6. Cropped Image saved to {output_file}")

    # Convert PIL -> numpy BGR uint8
    cropped_np = np.array(cropped_pil)
    if cropped_np.ndim == 3 and cropped_np.shape[2] == 4:
        cropped_np = cropped_np[:, :, :3]
    cropped_bgr = cv2.cvtColor(cropped_np, cv2.COLOR_RGB2BGR)
    cropped_bgr = np.ascontiguousarray(cropped_bgr, dtype=np.uint8)
    return cropped_bgr


# CLI for quick testing
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="image path")
    parser.add_argument("--out", default=CROPPED_OUTPUT_PATH, help="output directory")
    args = parser.parse_args()
    img = args.image
    detect_card(img, image_path=img)
