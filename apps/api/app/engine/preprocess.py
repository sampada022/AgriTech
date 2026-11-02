import cv2
import numpy as np
from typing import Tuple, Dict

def check_image_quality(img_bgr: np.ndarray) -> Tuple[float, str]:
    """
    Computes image blur and exposure metrics.
    Blur = variance of Laplacian
    Exposure = share of clipped pixels (<= 2 or >= 253)
    Returns (quality_score: 0.0 - 1.0, warning: str)
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    total_pixels = gray.size
    clipped_dark = np.sum(gray <= 2)
    clipped_bright = np.sum(gray >= 253)
    clipped_pct = (clipped_dark + clipped_bright) / float(total_pixels)

    # Laplacian var: typical sharp drone nadir >= 150.0
    blur_score = min(1.0, laplacian_var / 250.0)
    exposure_penalty = max(0.0, 1.0 - (clipped_pct * 4.0))

    quality = round(blur_score * exposure_penalty, 3)

    warning = ""
    if laplacian_var < 80.0:
        warning = "Image appears blurry; re-fly recommended if early pest detection fails."
    elif clipped_pct > 0.15:
        warning = "High exposure clipping detected; sun glare or heavy shadows present."

    return max(0.1, min(1.0, quality)), warning

def gray_world_normalise(img_bgr: np.ndarray) -> np.ndarray:
    """
    Applies gray-world white balance without CLAHE or contrast warping
    so GLCM texture remains undistorted.
    """
    result = img_bgr.astype(np.float32)
    mean_b = np.mean(result[:, :, 0])
    mean_g = np.mean(result[:, :, 1])
    mean_r = np.mean(result[:, :, 2])
    
    gray_mean = (mean_b + mean_g + mean_r) / 3.0
    if mean_b > 0: result[:, :, 0] *= (gray_mean / mean_b)
    if mean_g > 0: result[:, :, 1] *= (gray_mean / mean_g)
    if mean_r > 0: result[:, :, 2] *= (gray_mean / mean_r)

    return np.clip(result, 0, 255).astype(np.uint8)

def compute_canopy_mask(img_bgr: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Extracts vegetation canopy:
    1. Excess Green ExG = 2g - r - b on chromatic coordinates
    2. Exclude deep shadow via low HSV value
    3. Otsu thresholding on chromatic green contrast
    4. Morphological opening and closing
    Returns (binary_mask (uint8: 0 or 255), canopy_percentage)
    """
    img_float = img_bgr.astype(np.float32)
    b, g, r = img_float[:, :, 0], img_float[:, :, 1], img_float[:, :, 2]
    total = r + g + b + 1e-6
    rn, gn, bn = r / total, g / total, b / total

    exg = 2.0 * gn - rn - bn
    # Crop canopy is where excess green is positive
    green_mask = (exg > 0.05) & (g > r)

    # Exclude deep shadows using HSV V channel
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    not_shadow = v_channel > 30

    combined = green_mask & not_shadow

    # Morphological clean
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    clean_mask = cv2.morphologyEx(combined.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel)

    canopy_pct = round(float(np.sum(clean_mask > 0)) / float(clean_mask.size) * 100.0, 1)
    return clean_mask, canopy_pct
