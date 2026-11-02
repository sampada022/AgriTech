import cv2
import numpy as np
from app.sim.generate import generate_synthetic_field
from app.engine.preprocess import check_image_quality, gray_world_normalise, compute_canopy_mask
from app.engine.indices import compute_vegetation_indices
from app.engine.tiles import grid_tiling
from app.engine.anomaly import score_tile_anomalies
from app.engine.cluster import cluster_flagged_tiles
from app.engine.render import render_anomaly_heatmap_rgba

def test_tiles_anomaly_and_clustering_pipeline():
    # 1. Generate small synthetic canvas
    img_bgr, mask, bounds, patches = generate_synthetic_field(
        scenario="mixed", seed=42, width=1024, height=768
    )
    assert img_bgr.shape == (768, 1024, 3)

    # 2. Preprocess & Indices
    normed = gray_world_normalise(img_bgr)
    canopy, canopy_pct = compute_canopy_mask(normed)
    vari, gli, greenness = compute_vegetation_indices(normed)

    # 3. Tiling (48px)
    tiles = grid_tiling(normed, greenness, canopy, tile_size=48)
    assert len(tiles) > 100
    valid_tiles = [t for t in tiles if t["features"]["valid_canopy"] == 1.0]
    assert len(valid_tiles) > 30

    # 4. Anomaly scoring
    scored_tiles = score_tile_anomalies(tiles, tau=1.8)
    flagged = [t for t in scored_tiles if t["flagged"]]
    assert len(flagged) > 0, "Anomaly detection must flag stressed tiles"

    # 5. DBSCAN Clustering in local metres
    clusters = cluster_flagged_tiles(
        scored_tiles,
        gsd_cm=3.0,
        tile_size_px=48,
        eps_multiplier=1.6,
        min_samples=2,
        min_area_m2=2.0,
        lat0=12.5240,
        lon0=76.9000,
        img_width_px=1024,
        img_height_px=768
    )

    assert len(clusters) > 0, "DBSCAN must form at least one polygon cluster"
    first = clusters[0]
    assert first["area_m2"] >= 2.0
    assert "geometry" in first
    assert first["geometry"]["type"] == "Polygon"
    assert len(first["geometry"]["coordinates"][0]) >= 4

    # 6. RGBA Anomaly Heatmap Rendering
    rgba_heat = render_anomaly_heatmap_rgba(scored_tiles, 1024, 768, tile_size=48)
    assert rgba_heat.shape == (768, 1024, 4)

