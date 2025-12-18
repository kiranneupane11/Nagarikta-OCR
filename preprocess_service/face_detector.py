import cv2
import numpy as np

def face_detector(image_input: np.ndarray) -> str:
    # Load image
    if not isinstance(image_input, np.ndarray) or image_input.size == 0:
        print("Error: Invalid or empty image input (not a NumPy array or array is empty).")
        return "unknown"

    
    # Load Pre-trained Face Detector 
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        image_input, 
        scaleFactor=1.1, 
        minNeighbors=5, 
        minSize=(30, 30) 
    )
    
    if len(faces) > 0:
        return "front" 
    else:
        return "back"  