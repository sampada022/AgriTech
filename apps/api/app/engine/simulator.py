"""Synthetic field simulator (TRD 8.2, feature F2).

Produces a field image, a per-pixel class mask, a bounds file and a patch list. Everything it
makes is synthetic and carries that label downstream.

    python -m app.engine.simulator --scenario mixed --seed 7 --out ./sim_out
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from app.engine.geo import Bounds, bounds_from_centre

CLASS_HEALTHY = 0
CLASS_PEST = 1
CLASS_DROUGHT = 2
CLASS_NUTRIENT = 3
CLASS_DISTRACTOR = 4
CLASS_NAMES = {0: "healthy", 1: "pest", 2: "drought", 3: "nutrient", 4: "distractor"}

SCENARIOS = ("healthy", "pest", "mixed")
DIFFICULTIES = {
    # noise scales canopy variation, contrast scales how strongly stress shows.
    "easy": {"noise": 0.7, "contrast": 1.0},
    "medium": {"noise": 1.0, "contrast": 0.8},
    "hard": {"noise": 1.35, "contrast": 0.6},
}

HEALTHY_RGB = np.array([0.20, 0.40, 0.13], dtype=np.float32)
DAMAGE_RGB = np.array([0.60, 0.47, 0.20], dtype=np.float32)
HOLE_RGB = np.array([0.30, 0.23, 0.15], dtype=np.float32)
STRAW_RGB = np.array([0.50, 0.46, 0.22], dtype=np.float32)
NUTRIENT_RGB = np.array([0.42, 0.47, 0.17], dtype=np.float32)
SOIL_RGB = np.array([0.47, 0.37, 0.28], dtype=np.float32)
WATER_RGB = np.array([0.30, 0.38, 0.46], dtype=np.float32)


@dataclass
class SimConfig:
    scenario: str = "mixed"
    difficulty: str = "medium"
    seed: int = 7
    width: int = 4096
    height: int = 3072
    gsd_m: float = 0.03
    centre_lat: float = 12.5231
    centre_lon: float = 76.8951
    # Overrides for tests and scenario design. None means "use the scenario default".
    n_pest: int | None = None
    n_drought: int | None = None
    n_nutrient: int | None = None
    # Share of pest patches rendered faintly, which the mixed scenario uses to land some
    # genuine patches in the "uncertain" class before any feedback (TRD 6.7).
    faint_share: float | None = None
    faint_strength: float = 0.5


@dataclass
class SimResult:
    image: np.ndarray  # H x W x 3 uint8 RGB
    mask: np.ndarray  # H x W uint8 class ids
    bounds: Bounds
    patches: list[dict] = field(default_factory=list)
    config: SimConfig | None = None


def _fbm(
    shape: tuple[int, int], rng: np.random.Generator, cell_px: float, octaves: int = 3
) -> np.ndarray:
    """Multi-octave value noise scaled to roughly zero mean and unit spread."""
    h, w = shape
    out = np.zeros(shape, dtype=np.float32)
    amplitude = 1.0
    total = 0.0
    for i in range(octaves):
        cell = max(1.0, cell_px / (2**i))
        gh, gw = max(2, int(h / cell) + 2), max(2, int(w / cell) + 2)
        grid = rng.standard_normal((gh, gw)).astype(np.float32)
        out += amplitude * cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
        total += amplitude
        amplitude *= 0.5
    out /= total
    return out / (out.std() + 1e-6)


def _smoothstep(x: np.ndarray) -> np.ndarray:
    t = np.clip(x, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _blend_textured(
    image: np.ndarray, colour: np.ndarray, amount: np.ndarray, brightness: np.ndarray
) -> None:
    """Shift hue toward `colour` while keeping row and leaf structure.

    Abiotic stress recolours a canopy without removing it. Blending to a flat colour would erase
    the rows, and the texture cues would then separate biotic from abiotic far too easily.
    """
    target = colour[None, None, :] * brightness[..., None]
    image += (target - image) * amount[..., None]


class _Occupancy:
    """Keeps features apart so ground truth stays attributable to one cause."""

    def __init__(self) -> None:
        self.circles: list[tuple[float, float, float]] = []

    def free(self, x: float, y: float, r: float) -> bool:
        return all((x - cx) ** 2 + (y - cy) ** 2 > (r + cr) ** 2 for cx, cy, cr in self.circles)

    def add(self, x: float, y: float, r: float) -> None:
        self.circles.append((x, y, r))


def _place(rng, occ: _Occupancy, w: int, h: int, r_px: float, margin_px: float, tries: int = 200):
    edge = r_px + margin_px
    if 2 * edge >= min(w, h):
        return None  # does not fit on this canvas
    for _ in range(tries):
        x, y = rng.uniform(edge, w - edge), rng.uniform(edge, h - edge)
        if occ.free(x, y, r_px + margin_px):
            occ.add(x, y, r_px)
            return x, y
    return None


def _scenario_counts(cfg: SimConfig, rng: np.random.Generator) -> dict:
    defaults = {
        "healthy": {"pest": 0, "drought": 0, "nutrient": 0, "faint": 0.0},
        "pest": {"pest": int(rng.integers(6, 9)), "drought": 0, "nutrient": 0, "faint": 0.0},
        "mixed": {
            "pest": int(rng.integers(4, 9)),
            "drought": int(rng.integers(1, 3)),
            "nutrient": int(rng.integers(2, 4)),
            "faint": 0.5,
        },
    }[cfg.scenario]
    return {
        "pest": defaults["pest"] if cfg.n_pest is None else cfg.n_pest,
        "drought": defaults["drought"] if cfg.n_drought is None else cfg.n_drought,
        "nutrient": defaults["nutrient"] if cfg.n_nutrient is None else cfg.n_nutrient,
        "faint": defaults["faint"] if cfg.faint_share is None else cfg.faint_share,
    }


def simulate(cfg: SimConfig) -> SimResult:
    if cfg.scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {cfg.scenario}")
    if cfg.difficulty not in DIFFICULTIES:
        raise ValueError(f"Unknown difficulty: {cfg.difficulty}")

    rng = np.random.default_rng(cfg.seed)
    diff = DIFFICULTIES[cfg.difficulty]
    w, h, gsd = cfg.width, cfg.height, cfg.gsd_m
    px_per_m = 1 / gsd
    shape = (h, w)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    counts = _scenario_counts(cfg, rng)

    # Canopy: sinusoidal rows, slow vigour variation and leaf-level grain.
    row_angle = float(rng.uniform(-0.5, 0.5))  # radians off the image x axis
    spacing_px = float(rng.uniform(0.6, 0.9)) * px_per_m
    across = -xx * np.sin(row_angle) + yy * np.cos(row_angle)
    wobble = _fbm(shape, rng, cell_px=900, octaves=2) * 6.0
    rows = np.sin(2 * np.pi * (across + wobble) / spacing_px)
    vigour = _fbm(shape, rng, cell_px=1400, octaves=4)
    grain = _fbm(shape, rng, cell_px=4, octaves=2)
    leaf = rng.standard_normal(shape).astype(np.float32)
    leaf = cv2.GaussianBlur(leaf, (0, 0), 0.8)
    leaf /= leaf.std() + 1e-6

    brightness = (
        1.0
        + 0.20 * rows
        + 0.05 * diff["noise"] * vigour
        + 0.09 * diff["noise"] * grain
        + 0.07 * diff["noise"] * leaf
    )
    image = np.empty((h, w, 3), dtype=np.float32)
    # Vigour also shifts hue slightly, so greenness is not perfectly flat in a healthy field.
    tint = 0.018 * diff["noise"] * vigour
    image[..., 0] = HEALTHY_RGB[0] * brightness - tint
    image[..., 1] = HEALTHY_RGB[1] * brightness + tint
    image[..., 2] = HEALTHY_RGB[2] * brightness
    mask = np.zeros(shape, dtype=np.uint8)
    occ = _Occupancy()
    patches: list[dict] = []

    # Distractors go first so stress features keep clear of them.
    _add_soil_track(image, mask, rng, w, h, px_per_m, xx, yy, patches, occ)
    _add_tree_shadow(image, mask, rng, w, h, px_per_m, xx, yy, patches, occ)
    _add_water_trough(image, mask, rng, w, h, px_per_m, patches, occ)

    for i in range(counts["drought"]):
        _add_drought(image, mask, rng, w, h, gsd, xx, yy, diff, i, patches, occ, shape, brightness)

    # Stripes are placed before the pests so pests avoid them.
    band_offsets = _add_nutrient(
        image, mask, rng, w, h, px_per_m, xx, yy, row_angle, diff, counts["nutrient"], patches,
        brightness,
    )

    for i in range(counts["pest"]):
        faint = rng.random() < counts["faint"]
        _add_pest(
            image, mask, rng, w, h, px_per_m, gsd, xx, yy, diff, i, faint,
            patches, occ, shape, band_offsets, row_angle, cfg.faint_strength,
        )

    # Sensor noise and a mild per-channel cast, so white balance has real work to do.
    image += rng.normal(0.0, 0.006 * diff["noise"], image.shape).astype(np.float32)
    image *= rng.uniform(0.97, 1.03, 3).astype(np.float32)
    rgb = (np.clip(image, 0, 1) * 255).astype(np.uint8)

    bounds = bounds_from_centre(cfg.centre_lat, cfg.centre_lon, w * gsd, h * gsd)
    return SimResult(image=rgb, mask=mask, bounds=bounds, patches=patches, config=cfg)


def _add_soil_track(image, mask, rng, w, h, px_per_m, xx, yy, patches, occ) -> None:
    width_m = float(rng.uniform(1.5, 2.5))
    half = width_m / 2 * px_per_m
    y0 = float(rng.uniform(0.15, 0.25)) * h
    slope = float(rng.uniform(-0.05, 0.05))
    curve = float(rng.uniform(20, 60))
    centre = y0 + slope * xx + curve * np.sin(xx / w * np.pi * 2)
    dist = np.abs(yy - centre)
    amount = _smoothstep((half + 6 - dist) / 12)
    tex = 1 + 0.08 * _fbm((h, w), rng, cell_px=10, octaves=2)
    soil = SOIL_RGB[None, None, :] * tex[..., None]
    image += (soil - image) * amount[..., None]
    mask[amount > 0.5] = CLASS_DISTRACTOR
    patches.append({"id": "track", "class": "distractor", "kind": "soil_track", "width_m": width_m})
    # Keep stress features off the track by reserving a chain of circles along it.
    for x in np.linspace(0, w, 24):
        cy = y0 + slope * x + curve * np.sin(x / w * np.pi * 2)
        occ.add(float(x), float(cy), half + 90)


def _add_tree_shadow(image, mask, rng, w, h, px_per_m, xx, yy, patches, occ) -> None:
    r_m = float(rng.uniform(4, 7))
    r = r_m * px_per_m
    pos = _place(rng, occ, w, h, r, 80)
    if pos is None:
        return
    cx, cy = pos
    warp = _fbm((h, w), rng, cell_px=260, octaves=3) * r * 0.16
    dist = np.hypot((xx - cx) / 1.35, yy - cy) + warp
    amount = _smoothstep((r - dist) / 28)
    darkness = float(rng.uniform(0.34, 0.45))
    image *= (1 - (1 - darkness) * amount)[..., None]
    mask[amount > 0.5] = CLASS_DISTRACTOR
    patches.append(
        {"id": "shadow", "class": "distractor", "kind": "tree_shadow", "radius_m": r_m,
         "center_px": [round(cx), round(cy)]}
    )


def _add_water_trough(image, mask, rng, w, h, px_per_m, patches, occ) -> None:
    tw, th = int(3.0 * px_per_m), int(1.2 * px_per_m)
    pos = _place(rng, occ, w, h, tw / 1.5, 60)
    if pos is None:
        return
    cx, cy = int(pos[0]), int(pos[1])
    x0, y0 = cx - tw // 2, cy - th // 2
    image[y0 - 4 : y0 + th + 4, x0 - 4 : x0 + tw + 4] = SOIL_RGB * 0.7
    image[y0:y0 + th, x0:x0 + tw] = WATER_RGB
    mask[y0 - 4 : y0 + th + 4, x0 - 4 : x0 + tw + 4] = CLASS_DISTRACTOR
    patches.append(
        {"id": "trough", "class": "distractor", "kind": "water_trough", "center_px": [cx, cy]}
    )


def _add_drought(image, mask, rng, w, h, gsd, xx, yy, diff, i, patches, occ, shape, brightness) -> None:
    # The cap only matters on the small canvases tests use. The full canvas is about 11,000 m^2.
    target_area = min(float(rng.uniform(200, 800)), w * h * gsd * gsd * 0.1)
    aspect = float(rng.uniform(1.0, 1.6))
    b_px = np.sqrt(target_area / (np.pi * aspect)) / gsd
    a_px = b_px * aspect
    pos = _place(rng, occ, w, h, a_px, 120)
    if pos is None:
        return
    cx, cy = pos
    warp = _fbm(shape, rng, cell_px=700, octaves=2) * 0.13
    dist = np.hypot((xx - cx) / a_px, (yy - cy) / b_px) + warp
    # Soft edge running several metres, which is what separates it from a pest patch.
    edge = _smoothstep((1.12 - dist) / 0.42)
    gradient = 0.75 + 0.25 * _fbm(shape, rng, cell_px=1100, octaves=1)
    amount = np.clip(edge * gradient, 0, 1) * 0.72 * (0.55 + 0.45 * diff["contrast"])
    _blend_textured(image, STRAW_RGB, amount, brightness)
    region = (edge > 0.35) & (mask == CLASS_HEALTHY)
    mask[region] = CLASS_DROUGHT
    patches.append(
        {
            "id": f"drought_{i}",
            "class": "drought",
            "center_px": [round(cx), round(cy)],
            "area_m2": round(float(region.sum()) * gsd * gsd, 1),
        }
    )


def _add_nutrient(
    image, mask, rng, w, h, px_per_m, xx, yy, row_angle, diff, count, patches, brightness
) -> list[tuple[float, float]]:
    """Bands along the row direction with mild, uniform yellowing."""
    bands: list[tuple[float, float]] = []
    across = -xx * np.sin(row_angle) + yy * np.cos(row_angle)
    lo, hi = float(across.min()), float(across.max())
    for i in range(count):
        width_m = float(rng.uniform(2, 4))
        half = width_m / 2 * px_per_m
        for _ in range(100):
            offset = float(rng.uniform(lo + 0.1 * (hi - lo), hi - 0.1 * (hi - lo)))
            if all(abs(offset - o) > half + oh + 3 * px_per_m for o, oh in bands):
                break
        else:
            continue
        bands.append((offset, half))
        dist = np.abs(across - offset)
        edge = _smoothstep((half + 12 - dist) / 24)
        amount = edge * 0.58 * (0.6 + 0.4 * diff["contrast"])
        _blend_textured(image, NUTRIENT_RGB, amount, brightness)
        region = (edge > 0.5) & (mask == CLASS_HEALTHY)
        mask[region] = CLASS_NUTRIENT
        patches.append(
            {
                "id": f"nutrient_{i}",
                "class": "nutrient",
                "width_m": round(width_m, 2),
                "across_offset_px": round(offset),
                "area_m2": round(float(region.sum()) / (px_per_m * px_per_m), 1),
            }
        )
    return bands


def _add_pest(
    image, mask, rng, w, h, px_per_m, gsd, xx, yy, diff, i, faint,
    patches, occ, shape, bands, row_angle, faint_strength,
) -> None:
    r_m = float(rng.uniform(0.8, 3.0))
    r = r_m * px_per_m
    pos = None
    for _ in range(60):
        candidate = _place(rng, occ, w, h, r * 1.5, 40, tries=20)
        if candidate is None:
            continue
        across = -candidate[0] * np.sin(row_angle) + candidate[1] * np.cos(row_angle)
        if all(abs(across - o) > oh + r * 1.5 + 40 for o, oh in bands):
            pos = candidate
            break
        occ.circles.pop()
    if pos is None:
        return
    cx, cy = pos

    # Work on a crop: each patch only touches a few hundred pixels across.
    pad = int(r * 2.2) + 8
    x0, x1 = max(0, int(cx) - pad), min(w, int(cx) + pad)
    y0, y1 = max(0, int(cy) - pad), min(h, int(cy) + pad)
    crop_shape = (y1 - y0, x1 - x0)
    cxx, cyy = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]
    warp = _fbm(crop_shape, rng, cell_px=max(12.0, r / 1.5), octaves=3) * r * 0.24
    dist = np.hypot(cxx - cx, cyy - cy) + warp
    inside = dist < r

    # Thinning and holes: blotchy damaged leaves mixed with healthy ones, plus some gaps.
    density = float(rng.uniform(0.30, 0.40) if faint else rng.uniform(0.42, 0.60))
    strength = diff["contrast"] * (faint_strength if faint else 1.0)
    blotch = _fbm(crop_shape, rng, cell_px=5, octaves=2)
    damaged = inside & (blotch > np.quantile(blotch[inside], 1 - density))
    holes = inside & (blotch > np.quantile(blotch[inside], 1 - density * 0.25))

    view = image[y0:y1, x0:x1]
    speckle = 1 + 0.12 * _fbm(crop_shape, rng, cell_px=3, octaves=1)
    target = DAMAGE_RGB[None, None, :] * speckle[..., None]
    view[damaged] += (target[damaged] - view[damaged]) * min(1.0, 0.95 * strength)
    view[holes] += (HOLE_RGB - view[holes]) * min(1.0, 0.85 * strength)
    # Faint halo where damage is just starting.
    halo = _smoothstep((r * 1.45 - dist) / (r * 0.45)) * (dist >= r)
    view += (STRAW_RGB - view) * (halo * 0.10 * strength)[..., None]

    mask[y0:y1, x0:x1][inside] = CLASS_PEST
    patches.append(
        {
            "id": f"pest_{i}",
            "class": "pest",
            "center_px": [round(cx), round(cy)],
            "radius_m": round(r_m, 2),
            "area_m2": round(float(inside.sum()) * gsd * gsd, 2),
            "density": round(density, 2),
            "faint": bool(faint),
        }
    )


def save(result: SimResult, out_dir: Path) -> dict[str, Path]:
    """Write image, mask, bounds and patch list. One command, one folder (F2)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "image": out_dir / "field.jpg",
        "mask": out_dir / "mask.png",
        "bounds": out_dir / "bounds.json",
        "patches": out_dir / "patches.json",
    }
    cv2.imwrite(
        str(paths["image"]),
        cv2.cvtColor(result.image, cv2.COLOR_RGB2BGR),
        [cv2.IMWRITE_JPEG_QUALITY, 95],
    )
    cv2.imwrite(str(paths["mask"]), result.mask)
    paths["bounds"].write_text(json.dumps(result.bounds.as_dict(), indent=2))
    cfg = result.config
    paths["patches"].write_text(
        json.dumps(
            {
                "synthetic": True,
                "scenario": cfg.scenario if cfg else None,
                "difficulty": cfg.difficulty if cfg else None,
                "seed": cfg.seed if cfg else None,
                "gsd_m": cfg.gsd_m if cfg else None,
                "class_ids": CLASS_NAMES,
                "patches": result.patches,
            },
            indent=2,
        )
    )
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic field.")
    parser.add_argument("--scenario", choices=SCENARIOS, default="mixed")
    parser.add_argument("--difficulty", choices=list(DIFFICULTIES), default="medium")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path("sim_out"))
    args = parser.parse_args()
    result = simulate(SimConfig(args.scenario, args.difficulty, args.seed))
    paths = save(result, args.out)
    print(json.dumps({k: str(v) for k, v in paths.items()}, indent=2))


if __name__ == "__main__":
    main()
