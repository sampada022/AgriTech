import cv2
import numpy as np

def render_anomaly_heatmap_rgba(
    tiles: list,
    img_width: int,
    img_height: int,
    tile_size: int = 48
) -> np.ndarray:
    """
    Renders tile anomaly scores into an upsampled RGBA heatmap overlay:
    - Transparent for low scores
    - Yellow for mild stress
    - Vivid Red for high anomaly
    """
    grid_w = img_width // tile_size
    grid_h = img_height // tile_size
    grid = np.zeros((grid_h, grid_w), dtype=np.float32)

    for t in tiles:
        gx = t["x_px"] // tile_size
        gy = t["y_px"] // tile_size
        if gy < grid_h and gx < grid_w:
            grid[gy, gx] = t.get("anomaly_score", 0.0)

    # Normalize grid 0..4 to 0..255
    scaled = np.clip(grid / 3.5 * 255.0, 0, 255).astype(np.uint8)

    # Upsample with smooth bicubic interpolation to original size
    upsampled = cv2.resize(scaled, (img_width, img_height), interpolation=cv2.INTER_CUBIC)

    # Apply Colormap: Jet / Hot
    colored_bgr = cv2.applyColorMap(upsampled, cv2.COLORMAP_JET)

    # Generate Alpha channel (transparent where anomaly is negligible)
    alpha = np.clip((upsampled.astype(np.float32) - 40.0) / 160.0 * 200.0, 0, 200).astype(np.uint8)

    rgba = np.dstack([colored_bgr, alpha])
    return rgba

