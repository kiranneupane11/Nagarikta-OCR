# preprocessing.py
import cv2
import numpy as np

# Avoid OpenCV thread conflicts with other native libs
cv2.setNumThreads(0)

def skew_correction(gray_image):
    """
    Input: 2D uint8 grayscale image
    Output: rotated grayscale image (uint8)
    """
    orig = gray_image.copy().astype(np.uint8)

    # Otsu threshold + blur -> edges
    _, thresh = cv2.threshold(orig, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    blur = cv2.GaussianBlur(thresh, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)

    hough_lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180,
                                 threshold=100, minLineLength=100, maxLineGap=10)

    slopes = []
    if hough_lines is not None:
        for line in hough_lines:
            x1, y1, x2, y2 = line[0]
            dx = (x2 - x1)
            if dx != 0:
                slopes.append((y2 - y1) / dx)

    rad_angles = [np.arctan(s) for s in slopes if np.isfinite(s)]
    deg_angles = [np.degrees(a) for a in rad_angles]

    if deg_angles:
        histo = np.histogram(deg_angles, bins=100)
        rotation_number = float(histo[1][np.argmax(histo[0])])
        if rotation_number > 45:
            rotation_number = -(90 - rotation_number)
        elif rotation_number < -45:
            rotation_number = 90 - abs(rotation_number)
    else:
        rotation_number = 0.0

    (h, w) = orig.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, rotation_number, 1.0)
    rotated = cv2.warpAffine(orig, matrix, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    print(f"Image rotated by {rotation_number}")
    return rotated.astype(np.uint8)


def resize_image(rotated_image):
    (h, w) = rotated_image.shape[:2]
    max_dim = 640
    if w > h:
        ratio = max_dim / float(w)
        new_w = max_dim
        new_h = int(h * ratio)
    else:
        ratio = max_dim / float(h)
        new_h = max_dim
        new_w = int(w * ratio)
    scaled_img = cv2.resize(rotated_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    print(f"Original dimensions: ({w}x{h})")
    print(f"Scaled dimensions: ({new_w}x{new_h})")
    return scaled_img


def add_border(scaled_img):
    # Convert grayscale -> BGR if needed
    if scaled_img.ndim == 2:
        scaled_img = cv2.cvtColor(scaled_img, cv2.COLOR_GRAY2BGR)

    border_image = cv2.copyMakeBorder(
        src=scaled_img,
        top=20, bottom=20, left=20, right=20,
        borderType=cv2.BORDER_CONSTANT,
        value=(255, 255, 255)
    )
    bor_h, bor_w = border_image.shape[:2]
    print(f"Dimensions with border:({bor_w}x{bor_h})")
    return border_image


def preprocess_pipeline(cropped_image):
    """
    Expects:  numpy ndarray (uint8)
    Returns:  numpy ndarray (uint8, C-contiguous)
    """
    if not isinstance(cropped_image, np.ndarray):
        raise TypeError("preprocess_pipeline expects a numpy.ndarray")

    # ensure correct dtype
    img = cropped_image.astype(np.uint8, copy=False)

    # Convert to grayscale for skew detection
    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    rotated_gray = skew_correction(gray_image)
    resized_gray = resize_image(rotated_gray)
    final_bgr = add_border(resized_gray)

    final_bgr = np.ascontiguousarray(final_bgr, dtype=np.uint8)
    return final_bgr


