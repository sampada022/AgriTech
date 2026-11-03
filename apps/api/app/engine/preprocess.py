"""Steps 1 to 4 of the pipeline (TRD 6.2): quality, normalise, canopy mask, indices."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

TARGET_GSD_M = 0.03
MAX_LONG_EDGE = 4096

# Blur and exposure thresholds, checked on real sugarcane and wheat orthomosaics as well as on the
# simulator. Sharp images measured 100 to 800, and the simulator with a 3 px blur measured under 3.
BLUR_VAR_GOOD = 60.0
BLUR_VAR_BAD = 12.0
CLIPPED_SHARE_OK = 0.03
CLIPPED_SHARE_BAD = 0.25

# Gray-world gains are damped. A canopy image is green on average by nature, so a full correction
# pushes mean ExG to zero. On the simulator that drops drought and nutrient zones out of the
# canopy mask (7% and 2% kept), so they would be drawn grey instead of scored. See test_preprocess.
WB_STRENGTH = 0.5
WB_GAIN_LIMITS = (0.75, 1.35)

# Otsu splits the largest two modes, which in a mostly green field can be healthy vs yellowing.
# Stressed canopy must stay canopy, so the threshold is capped well under stressed-crop ExG.
# A field that is mostly soil has no second mode at all, and Otsu then lands in the noise below
# zero, which reads bare soil as canopy. So the threshold has a floor too.
EXG_THRESHOLD_CEILING = 0.04
EXG_THRESHOLD_FLOOR = 0.0
SHADOW_BRIGHTNESS_RATIO = 0.62

# Morphology sizes are in metres, so they mean the same thing at any working resolution.
OPEN_M = 0.15  # removes specks
CLOSE_M = 0.75  # wider than damage speckle, so holes in a pest patch are not read as bare soil
SHADOW_BLUR_M = 0.3
# Radius of the "is this pixel darker than its surroundings" neighbourhood. Real shadow (tree lines,
# equipment, cloud) is narrow relative to this; a genuinely denser or different-crop patch many
# metres across is not, so it survives comparison against a reference this local. A single global
# median reference (the previous approach) instead compared every pixel to the whole image's
# brightness, which reads an entire dense, darker-canopy field as "shadow" next to a paler one.
SHADOW_LOCAL_RADIUS_M = 6.0

# Orthomosaics have large empty margins outside the flown area. JPEG re-encoding leaves them
# near-black rather than exactly black, hence a small tolerance. The opening keeps dark gaps inside
# the canopy from being mistaken for no-data, and the dilation swallows the ringing at the border.
NODATA_MAX_VALUE = 8
NODATA_MIN_BLOCK_PX = 15
NODATA_EDGE_PX = 5


@dataclass
class QualityReport:
    score: float
    blur_variance: float
    clipped_share: float
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "score": round(self.score, 3),
            "blur_variance": round(self.blur_variance, 1),
            "clipped_share": round(self.clipped_share, 4),
            "warnings": self.warnings,
        }


@dataclass
class CanopyResult:
    mask: np.ndarray  # bool
    canopy_pct: float  # share of pixels that hold image data
    exg: np.ndarray
    exg_threshold: float
    shadow_pct: float
    nodata: np.ndarray  # bool
    data_fraction: float  # share of the image rectangle that holds image data


@dataclass
class IndexLayers:
    vari: np.ndarray
    gli: np.ndarray
    greenness: np.ndarray


def _odd_px(metres: float, gsd_m: float, minimum: int = 3) -> int:
    px = max(minimum, int(round(metres / gsd_m)))
    return px if px % 2 == 1 else px + 1


def resample_to_working(rgb: np.ndarray, gsd_m: float) -> tuple[np.ndarray, float]:
    """Downsample to about 3 cm per pixel with the long edge capped. Never upsamples."""
    h, w = rgb.shape[:2]
    scale = min(1.0, gsd_m / TARGET_GSD_M, MAX_LONG_EDGE / max(h, w))
    if scale >= 0.999:
        return rgb, 1.0
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    return cv2.resize(rgb, size, interpolation=cv2.INTER_AREA), scale


def nodata_mask(rgb: np.ndarray) -> np.ndarray:
    """True where an orthomosaic holds no image: large near-black blocks, usually the margins."""
    dark = (rgb.max(axis=2) <= NODATA_MAX_VALUE).astype(np.uint8)
    if not dark.any():
        return np.zeros(rgb.shape[:2], dtype=bool)
    block = np.ones((NODATA_MIN_BLOCK_PX, NODATA_MIN_BLOCK_PX), np.uint8)
    solid = cv2.morphologyEx(dark, cv2.MORPH_OPEN, block)
    if not solid.any():
        return np.zeros(rgb.shape[:2], dtype=bool)
    edge = np.ones((2 * NODATA_EDGE_PX + 1, 2 * NODATA_EDGE_PX + 1), np.uint8)
    return cv2.dilate(solid, edge).astype(bool)


def quality_check(rgb: np.ndarray, nodata: np.ndarray | None = None) -> QualityReport:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    if nodata is not None and nodata.any() and not nodata.all():
        data = ~nodata
        blur_var = float(laplacian[data].var())
        values = gray[data]
    else:
        blur_var = float(laplacian.var())
        values = gray.ravel()
    clipped = float(np.mean((values <= 4) | (values >= 251)))

    span = np.log(BLUR_VAR_GOOD) - np.log(BLUR_VAR_BAD)
    blur_score = float(np.clip((np.log(max(blur_var, 1e-6)) - np.log(BLUR_VAR_BAD)) / span, 0, 1))
    exposure_score = float(
        np.clip(1 - (clipped - CLIPPED_SHARE_OK) / (CLIPPED_SHARE_BAD - CLIPPED_SHARE_OK), 0, 1)
    )

    warnings = []
    if blur_score < 0.5:
        warnings.append(
            "This image looks blurry, so small patches may be missed. Re-fly slower or in less "
            "wind if you can."
        )
    if exposure_score < 0.5:
        warnings.append(
            "Parts of this image are too bright or too dark to read. Re-fly with a lower "
            "exposure or at a different time of day."
        )
    # Floored so one weak measure lowers confidence without zeroing every hotspot on the map.
    score = max(0.15, min(blur_score, exposure_score))
    return QualityReport(score, blur_var, clipped, warnings)


def gray_world(
    rgb: np.ndarray, strength: float = WB_STRENGTH, nodata: np.ndarray | None = None
) -> np.ndarray:
    """Damped gray-world white balance. Returns float32 RGB in 0..1, with no contrast change."""
    img = rgb.astype(np.float32) / 255.0
    pixels = img[~nodata] if nodata is not None and nodata.any() and not nodata.all() else img
    means = pixels.reshape(-1, 3).mean(axis=0)
    gray = float(means.mean())
    gains = np.clip((gray / np.maximum(means, 1e-4)) ** strength, *WB_GAIN_LIMITS)
    return np.clip(img * gains.astype(np.float32), 0, 1)


def _chromatic_exg(norm: np.ndarray) -> np.ndarray:
    total = norm.sum(axis=2) + 1e-6
    r, g, b = norm[..., 0] / total, norm[..., 1] / total, norm[..., 2] / total
    return 2 * g - r - b


def canopy_mask(
    norm: np.ndarray, gsd_m: float = TARGET_GSD_M, nodata: np.ndarray | None = None
) -> CanopyResult:
    """ExG plus capped Otsu, open and close, then remove shadows by brightness."""
    if nodata is None:
        nodata = np.zeros(norm.shape[:2], dtype=bool)
    data = ~nodata
    exg = _chromatic_exg(norm)

    # Otsu on a fixed ExG scale, so the threshold can be read back in ExG units.
    lo, hi = -0.5, 1.0
    scaled = ((np.clip(exg, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)
    sample = scaled[::4, ::4][data[::4, ::4]]
    if sample.size == 0:
        sample = scaled[::4, ::4].ravel()
    otsu_u8, _ = cv2.threshold(
        sample.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    otsu = lo + otsu_u8 / 255 * (hi - lo)
    threshold = float(np.clip(otsu, EXG_THRESHOLD_FLOOR, EXG_THRESHOLD_CEILING))

    binary = ((exg > threshold) & data).astype(np.uint8)
    open_px = _odd_px(OPEN_M, gsd_m)
    close_px = _odd_px(CLOSE_M, gsd_m)
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_px, open_px))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_px, close_px))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel)

    # Shadows are large and dark. Blur first so the dark troughs between rows are not caught.
    value = norm.max(axis=2)
    small = cv2.resize(value, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    small_data = cv2.resize(
        data.astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST
    ).astype(bool)
    sigma = max(1.0, SHADOW_BLUR_M / gsd_m / 4)
    blurred = cv2.GaussianBlur(small, (0, 0), sigma)
    local_sigma = max(sigma * 4, SHADOW_LOCAL_RADIUS_M / gsd_m / 4)
    local_reference = cv2.GaussianBlur(blurred, (0, 0), local_sigma)
    shadow_small = ((blurred < SHADOW_BRIGHTNESS_RATIO * local_reference) & small_data).astype(np.uint8)
    shadow = cv2.resize(
        shadow_small, (norm.shape[1], norm.shape[0]), interpolation=cv2.INTER_NEAREST
    ).astype(bool)

    mask = binary.astype(bool) & ~shadow & data
    data_count = int(data.sum())
    return CanopyResult(
        mask=mask,
        canopy_pct=float(mask.sum() / data_count * 100) if data_count else 0.0,
        exg=exg,
        exg_threshold=threshold,
        shadow_pct=float((shadow & data).sum() / data_count * 100) if data_count else 0.0,
        nodata=nodata,
        data_fraction=float(data_count / data.size),
    )


def compute_indices(norm: np.ndarray, mask: np.ndarray) -> IndexLayers:
    """VARI and GLI. Greenness is the mean of the two, each z-scored over canopy pixels."""
    r, g, b = norm[..., 0], norm[..., 1], norm[..., 2]
    eps = 1e-3
    vari = np.clip((g - r) / (g + r - b + eps), -1, 1)
    gli = (2 * g - r - b) / (2 * g + r + b + eps)

    def z(index: np.ndarray) -> np.ndarray:
        values = index[mask] if mask.any() else index.ravel()
        return (index - values.mean()) / (values.std() + 1e-6)

    return IndexLayers(vari=vari, gli=gli, greenness=(z(vari) + z(gli)) / 2)
