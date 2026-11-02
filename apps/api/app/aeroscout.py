"""AeroScout analysis: RGB image -> tiles -> VARI + GLCM texture -> biotic/abiotic split -> DBSCAN hotspots -> walking route.

Everything here uses an ordinary RGB photo. Scores are RELATIVE to the field being analysed (a field is compared with
itself), so they rank where to walk first; they are not calibrated probabilities and not a pest diagnosis.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.feature import graycomatrix
from scipy import ndimage
from sklearn.cluster import DBSCAN

MAX_SIDE = 1600
TILE = 64            # tile size in analysis pixels (SAHI-style slicing with overlap)
OVERLAP = 0.25
LEVELS = 16          # grey levels for the GLCM
MIN_DROP = 0.04      # a tile must be at least this much less green (VARI) than the field median to count as stressed
Z_STRESS = 1.5       # ...and this many robust standard deviations below it
TEXTURE_RATIO = 1.3  # stressed tile with contrast >= 1.3x healthy median is "ragged" (biotic); below is "even" (abiotic)
TEXTURE_MARGIN = 1.0 # ...and at least this much GLCM contrast above it (stops a near-zero median making noise look ragged)
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def vari(rgb: np.ndarray) -> np.ndarray:
    """VARI = (G - R) / (G + R - B): a greenness score from ordinary camera colours."""
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    d = g + r - b
    d = np.where(np.abs(d) < 1e-3, 1e-3, d)
    return np.clip((g - r) / d, -1, 1)


def glcm_stats(gray16: np.ndarray) -> tuple[float, float]:
    """Contrast and entropy of a tile, averaged over 4 directions (distance 1)."""
    p = graycomatrix(gray16, [1], [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4], levels=LEVELS, symmetric=True, normed=True)[:, :, 0, :]
    i, j = np.indices((LEVELS, LEVELS))
    contrast = float(np.mean([np.sum(p[:, :, a] * (i - j) ** 2) for a in range(p.shape[2])]))
    ent = float(np.mean([-np.sum(q[q > 0] * np.log2(q[q > 0])) for q in (p[:, :, a] for a in range(p.shape[2]))]))
    return contrast, ent


def _robust_z(x: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, float, float]:
    med = float(np.median(x[mask])) if mask.any() else 0.0
    mad = float(np.median(np.abs(x[mask] - med))) * 1.4826 + 1e-6 if mask.any() else 1.0
    return (x - med) / mad, med, mad


def _ramp(t: np.ndarray) -> np.ndarray:
    """canopy green -> dry amber -> hotspot red, t in 0..1 -> uint8 RGB."""
    stops = np.array([[46, 90, 52], [200, 150, 30], [194, 57, 27]], dtype=np.float32)
    t = np.clip(t, 0, 1) * 2
    lo = np.clip(t.astype(int), 0, 1)
    f = (t - lo)[..., None]
    return (stops[lo] * (1 - f) + stops[lo + 1] * f).astype(np.uint8)


def _tour(points: list[tuple[float, float]], start: tuple[float, float]) -> list[int]:
    """Shortest walk from `start` visiting every point once (exact for <=8 points, nearest-neighbour above)."""
    n = len(points)
    if n == 0:
        return []
    d = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    if n <= 8:
        best = min(itertools.permutations(range(n)), key=lambda o: d(start, points[o[0]]) + sum(d(points[a], points[b]) for a, b in zip(o, o[1:])))
        return list(best)
    left, cur, order = set(range(n)), start, []
    while left:
        k = min(left, key=lambda i: d(cur, points[i]))
        order.append(k); left.remove(k); cur = points[k]
    return order


def analyze(src: Path, out_dir: Path, gsd_cm: float = 1.0, start: str = "bottom-left") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    ow, oh = im.size
    scale = min(1.0, MAX_SIDE / max(ow, oh))
    if scale < 1:
        im = im.resize((round(ow * scale), round(oh * scale)), Image.LANCZOS)
    W, H = im.size
    rgb = np.asarray(im)
    v = vari(rgb)
    gray = (np.asarray(im.convert("L")).astype(np.float32) / 256 * LEVELS).astype(np.uint8)

    stride = max(1, int(TILE * (1 - OVERLAP)))
    ys = list(range(0, max(1, H - TILE + 1), stride)); xs = list(range(0, max(1, W - TILE + 1), stride))
    R, C = len(ys), len(xs)
    # Thin non-green lines (tracks, bunds, field edges) are not crop: find pixels far below the median greenness, then
    # keep only blobs wider than ~21 px as possible stress. Everything else bad-and-thin is ignored.
    pm = float(np.median(v))
    bad = v < pm - 0.12
    blob = ndimage.binary_opening(bad, structure=np.ones((21, 21), bool))
    thin = bad & ~blob
    # Tracks and field edges are LONG thin lines; ragged pest speckle is thin too but short. Keep only the long ones.
    lab, n = ndimage.label(thin, structure=np.ones((3, 3), bool))
    long_ids = [i + 1 for i, sl in enumerate(ndimage.find_objects(lab)) if sl and max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) >= 150]
    thin = ndimage.binary_dilation(np.isin(lab, long_ids), iterations=4)  # include JPEG fringe next to the line
    tv = np.zeros((R, C), np.float32); tc = np.zeros_like(tv); te = np.zeros_like(tv); cover = np.zeros_like(tv)
    for r, y in enumerate(ys):
        for c, x in enumerate(xs):
            patch = v[y:y + TILE, x:x + TILE]; green = ~thin[y:y + TILE, x:x + TILE]
            cover[r, c] = green.mean()
            tv[r, c] = patch[green].mean() if green.any() else patch.mean()
            tc[r, c], te[r, c] = glcm_stats(gray[y:y + TILE, x:x + TILE])

    crop = cover >= 0.9  # tiles that touch a track or field edge are skipped (their colours are mixed)
    if crop.sum() < 10:
        crop = np.ones_like(crop, bool)
    z, vmed, _ = _robust_z(tv, crop)
    stressed = crop & (z < -Z_STRESS) & ((vmed - tv) > MIN_DROP)
    healthy = crop & ~stressed
    cmed = float(np.median(tc[healthy])) if healthy.any() else float(np.median(tc))
    emed = float(np.median(te[healthy])) if healthy.any() else float(np.median(te))
    ratio = tc / (cmed + 1e-6)
    biotic = stressed & (tc >= np.maximum(TEXTURE_RATIO * cmed, cmed + TEXTURE_MARGIN))
    abiotic = stressed & ~biotic

    # DBSCAN on biotic tile centres (units: tiles)
    hotspots: list[dict] = []
    idx = np.argwhere(biotic)
    if len(idx) >= 3:
        lab = DBSCAN(eps=2.0, min_samples=3).fit_predict(idx.astype(float))
        for k in sorted(set(lab) - {-1}):
            m = idx[lab == k]
            n = len(m)
            r0, c0, r1, c1 = m[:, 0].min(), m[:, 1].min(), m[:, 0].max(), m[:, 1].max()
            px0, py0, px1, py1 = xs[c0], ys[r0], xs[c1] + TILE, ys[r1] + TILE
            rr, cc = m[:, 0], m[:, 1]
            sev_score = float(np.mean(-z[rr, cc]) * math.sqrt(n))
            area_px = n * stride * stride
            area_m2 = area_px * (gsd_cm / 100 / scale) ** 2
            hotspots.append({
                "tiles": [[int(xs[c]), int(ys[r])] for r, c in m],
                "bbox": [px0, py0, px1, py1],
                "centroid": [float((px0 + px1) / 2), float((py0 + py1) / 2)],
                "n_tiles": int(n), "area_m2": round(area_m2, 1), "area_pct": round(100 * area_px / (W * H), 2),
                "vari": round(float(tv[rr, cc].mean()), 3), "vari_drop": round(float(vmed - tv[rr, cc].mean()), 3),
                "glcm_contrast": round(float(tc[rr, cc].mean()), 2), "glcm_entropy": round(float(te[rr, cc].mean()), 2),
                "texture_ratio": round(float(ratio[rr, cc].mean()), 2), "score": round(sev_score, 2),
            })
    hotspots.sort(key=lambda h: -h["score"])
    for i, h in enumerate(hotspots):
        h["id"] = LETTERS[i] if i < 26 else f"H{i + 1}"
        h["severity"] = "High" if h["score"] >= 8 or h["area_pct"] >= 4 else "Medium" if h["score"] >= 4 else "Low"
        h["pct"] = [round(h["centroid"][0] / W, 4), round(h["centroid"][1] / H, 4)]

    # walking route from a field corner
    sx, sy = {"bottom-left": (0.0, H), "bottom-right": (W, H), "top-left": (0.0, 0.0), "top-right": (W, 0.0)}.get(start, (0.0, H))
    order = _tour([tuple(h["centroid"]) for h in hotspots], (sx, sy))
    pts = [(sx, sy)] + [tuple(hotspots[i]["centroid"]) for i in order]
    dist_px = sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pts, pts[1:]))
    route = {"start": [sx / W, sy / H], "order": [hotspots[i]["id"] for i in order],
             "points": [[p[0] / W, p[1] / H] for p in pts], "distance_m": round(dist_px * gsd_cm / 100 / scale, 1)}
    for rank, i in enumerate(order):
        hotspots[i]["route_stop"] = rank + 1

    # images
    im.save(out_dir / "image.jpg", quality=88)
    up = lambda a: np.asarray(Image.fromarray(a).resize((W, H), Image.BILINEAR))
    Image.fromarray(up(_ramp((vmed - tv) / 0.3 * 1.0).clip(0, 255))).save(out_dir / "vari.png")
    t = np.clip(np.log2(np.maximum(ratio, 1e-3)) / 2 + 0.5, 0, 1)
    Image.fromarray(up(_ramp(t))).save(out_dir / "texture.png")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for r, c in np.argwhere(abiotic):
        d.rectangle([xs[c], ys[r], xs[c] + TILE, ys[r] + TILE], fill=(232, 178, 58, 70))
    for h in hotspots:
        for x, y in h["tiles"]:
            d.rectangle([x, y, x + TILE, y + TILE], fill=(255, 107, 66, 95))
    for h in hotspots:
        x0, y0, x1, y1 = h["bbox"]; d.rectangle([x0, y0, x1, y1], outline=(255, 255, 255, 255), width=3)
        d.rectangle([x0, y0, x1, y1], outline=(194, 57, 27, 255), width=1)
    d.line(pts, fill=(255, 255, 255, 255), width=5); d.line(pts, fill=(27, 31, 23, 255), width=2)
    try: f = ImageFont.load_default(size=22)
    except TypeError: f = ImageFont.load_default()
    for h in hotspots:
        cx, cy = h["centroid"]; d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=(194, 57, 27, 255), outline=(255, 255, 255, 255), width=2)
        d.text((cx - 6, cy - 11), h["id"], fill=(255, 255, 255, 255), font=f)
    Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB").save(out_dir / "overlay.jpg", quality=88)

    result = {
        "image": {"width": W, "height": H, "original_width": ow, "original_height": oh, "gsd_cm_assumed": gsd_cm},
        "grid": {"tile_px": TILE, "stride_px": stride, "rows": R, "cols": C, "tiles": int(R * C), "crop_tiles": int(crop.sum())},
        "field": {"vari_median": round(vmed, 3), "glcm_contrast_healthy_median": round(cmed, 2), "glcm_entropy_healthy_median": round(emed, 2),
                  "stressed_tiles": int(stressed.sum()), "biotic_tiles": int(biotic.sum()), "abiotic_tiles": int(abiotic.sum())},
        "hotspots": hotspots, "route": route,
        "abiotic": [{"x": int(xs[c]), "y": int(ys[r])} for r, c in np.argwhere(abiotic)],
        "method": "VARI + GLCM texture + DBSCAN on RGB tiles. Scores are relative to this field. Hotspots need ground confirmation.",
    }
    (out_dir / "result.json").write_text(json.dumps(result))
    return result
