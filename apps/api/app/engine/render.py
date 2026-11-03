"""Step 11 of the pipeline (TRD 6.2): overlay images, mask preview and hotspot crops."""

from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.engine.geo import FieldFrame
from app.engine.tiles import TileGrid

OVERLAY_BYTE_BUDGET = 1_500_000
RGB_ATTEMPTS = ((2048, 72), (1792, 68), (1536, 64), (1280, 60), (1024, 55), (800, 50))
ANALYTIC_LAYER_WIDTH = 1024
CROP_MAX_PX = 320
CROP_MIN_METRES = 3.0
EXCLUDED_GREY = np.array([120, 124, 130], dtype=np.float32)
# Fixed scale, so the heat layer does not need re-rendering when the sensitivity slider moves.
HEAT_MIN_A = 1.0
HEAT_MAX_A = 7.0
VARI_LOW = np.array([176, 42, 38], dtype=np.float32)
VARI_MID = np.array([240, 200, 70], dtype=np.float32)
VARI_HIGH = np.array([34, 139, 74], dtype=np.float32)


def encode_webp(image: np.ndarray, quality: int) -> bytes:
    mode = "RGBA" if image.shape[2] == 4 else "RGB"
    buffer = io.BytesIO()
    Image.fromarray(image, mode).save(buffer, "WEBP", quality=quality, method=3)
    return buffer.getvalue()


def _resize_to_width(image: np.ndarray, width: int) -> np.ndarray:
    h, w = image.shape[:2]
    if w <= width:
        return image
    return cv2.resize(image, (width, round(h * width / w)), interpolation=cv2.INTER_AREA)


def rgb_overlay(rgb: np.ndarray, nodata: np.ndarray | None = None) -> bytes:
    """Largest preview that fits the budget, so the map stays crisp and still loads over 4G.

    No-data margins become transparent, so the field sits cleanly on the basemap.
    """
    image = rgb
    if nodata is not None and nodata.any():
        alpha = np.where(nodata, 0, 255).astype(np.uint8)
        image = np.dstack((rgb, alpha))
    data = b""
    for width, quality in RGB_ATTEMPTS:
        data = encode_webp(_resize_to_width(image, width), quality)
        if len(data) <= OVERLAY_BYTE_BUDGET:
            return data
    return data


def _resize_tiles(values: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return cv2.resize(values.astype(np.float32), size, interpolation=cv2.INTER_NEAREST)


def _excluded_alpha(grid: TileGrid, size: tuple[int, int]) -> np.ndarray:
    """1 where a canopy tile was excluded from scoring. No-data tiles are not drawn at all."""
    excluded = ~grid.valid & (grid.nodata_frac < 0.5)
    return _resize_tiles(excluded, size)


def _nodata_alpha(grid: TileGrid, size: tuple[int, int]) -> np.ndarray:
    return _resize_tiles(grid.nodata_frac >= 0.5, size)


def vari_overlay(vari: np.ndarray, grid: TileGrid) -> bytes:
    """VARI colour layer: red through yellow to green, with excluded tiles drawn grey."""
    t = grid.tile_px
    cropped = vari[: grid.ny * t, : grid.nx * t].astype(np.float32)
    width = min(ANALYTIC_LAYER_WIDTH, cropped.shape[1])
    small = _resize_to_width(cropped, width)
    h, w = small.shape
    # VARI on healthy canopy sits at about 0.1 to 0.4, so that band gets most of the colour range.
    t_value = np.clip((small + 0.1) / 0.5, 0, 1)[..., None]
    low = np.clip(t_value * 2, 0, 1)
    high = np.clip(t_value * 2 - 1, 0, 1)
    out = VARI_LOW + (VARI_MID - VARI_LOW) * low
    out = out + (VARI_HIGH - out) * high
    excluded = _excluded_alpha(grid, (w, h))[..., None]
    out = out * (1 - excluded) + EXCLUDED_GREY * excluded
    alpha = (1 - _nodata_alpha(grid, (w, h))) * 255
    return encode_webp(np.dstack((out, alpha)).astype(np.uint8), 80)


def heat_overlay(anomaly: np.ndarray, grid: TileGrid) -> bytes:
    """Anomaly heat: transparent to yellow to red, with excluded tiles drawn grey.

    Stays visible below the threshold, so scouts can see areas the model did not flag (TRD 8.3).
    """
    t = grid.tile_px
    full_w = grid.nx * t
    width = min(ANALYTIC_LAYER_WIDTH, full_w)
    height = round(grid.ny * t * width / full_w)
    a = cv2.resize(anomaly.astype(np.float32), (width, height), interpolation=cv2.INTER_LINEAR)
    level = np.clip((a - HEAT_MIN_A) / (HEAT_MAX_A - HEAT_MIN_A), 0, 1)
    out = np.zeros((height, width, 4), dtype=np.float32)
    out[..., 0] = 250
    out[..., 1] = 220 * (1 - level) + 30 * level
    out[..., 2] = 60 * (1 - level)
    out[..., 3] = np.clip(level * 1.6, 0, 0.85) * 255
    excluded = _excluded_alpha(grid, (width, height)) > 0.5
    out[excluded, :3] = EXCLUDED_GREY
    out[excluded, 3] = 150
    out[_nodata_alpha(grid, (width, height)) > 0.5, 3] = 0
    return encode_webp(out.astype(np.uint8), 80)


def mask_preview(mask: np.ndarray) -> bytes:
    """Small canopy preview for the processing screen."""
    small = _resize_to_width((mask.astype(np.uint8) * 255), 640)
    out = np.zeros((*small.shape, 3), dtype=np.uint8)
    out[small >= 128] = (56, 168, 96)
    out[small < 128] = (60, 64, 72)
    return encode_webp(out, 70)


def thumbnail_jpeg(rgb: np.ndarray, width: int = 480) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(_resize_to_width(rgb, width)).save(buffer, "JPEG", quality=80)
    return buffer.getvalue()


def crop_jpeg(rgb: np.ndarray, polygon, frame: FieldFrame) -> bytes:
    """Hotspot thumbnail with a margin, at least 3 m across so tiny patches keep some context."""
    minx, miny, maxx, maxy = polygon.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    half_w = max(maxx - minx, CROP_MIN_METRES) / 2 * 1.25
    half_h = max(maxy - miny, CROP_MIN_METRES) / 2 * 1.25
    x0, y0 = frame.xy_to_px(cx - half_w, cy + half_h)
    x1, y1 = frame.xy_to_px(cx + half_w, cy - half_h)
    h, w = rgb.shape[:2]
    ix0, iy0 = max(0, int(x0)), max(0, int(y0))
    ix1, iy1 = min(w, int(x1) + 1), min(h, int(y1) + 1)
    crop = rgb[iy0:iy1, ix0:ix1]
    if crop.size == 0:
        crop = rgb[:1, :1]
    scale = CROP_MAX_PX / max(crop.shape[:2])
    if scale < 1:
        crop = cv2.resize(
            crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
        )
    buffer = io.BytesIO()
    Image.fromarray(crop).save(buffer, "JPEG", quality=82)
    return buffer.getvalue()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
