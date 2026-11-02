import cv2
import numpy as np
from typing import Tuple

def compute_vegetation_indices(img_bgr: np.ndarray, eps: float = 1e-6) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes visible-light vegetation proxies:
    - VARI = (G - R) / (G + R - B + eps) clipped [-1, 1]
    - GLI = (2G - R - B) / (2G + R + B + eps) clipped [-1, 1]
    - Combined Greenness = mean of z-scored VARI and GLI
    Note: Visible light proxies are NOT satellite NDVI and do not measure NIR reflectance.
    """
    img = img_bgr.astype(np.float32)
    b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    # VARI
    vari_denom = g + r - b + eps
    vari = (g - r) / vari_denom
    vari = np.clip(vari, -1.0, 1.0)

    # GLI
    gli_denom = 2.0 * g + r + b + eps
    gli = (2.0 * g - r - b) / gli_denom
    gli = np.clip(gli, -1.0, 1.0)

    # Robust standardization (mean of z-scores)
    vari_std = np.std(vari) or 1.0
    gli_std = np.std(gli) or 1.0
    z_vari = (vari - np.mean(vari)) / vari_std
    z_gli = (gli - np.mean(gli)) / gli_std
    greenness = (z_vari + z_gli) / 2.0

    return vari, gli, greenness

def render_vari_colormap(vari: np.ndarray) -> np.ndarray:
    """
    Renders VARI (-0.2 .. +0.6 typical active crop range) to an intuitive BGR false-color heatmap.
    Uses standard OpenCV COLORMAP_SUMMER or COLORMAP_JET.
    """
    # Scale -0.2 to 0.5 into 0 to 255
    scaled = np.clip((vari - (-0.2)) / (0.5 - (-0.2)) * 255.0, 0, 255).astype(np.uint8)
    colormap = cv2.applyColorMap(scaled, cv2.COLORMAP_SUMMER)
    return colormap
