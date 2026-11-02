import os
import cv2
import numpy as np
from app.engine.geo import latlon_to_xy, xy_to_latlon, compute_field_dimensions_m, haversine_distance_m
from app.engine.preprocess import check_image_quality, gray_world_normalise, compute_canopy_mask
from app.engine.indices import compute_vegetation_indices, render_vari_colormap
from app.sim.generate import generate_synthetic_field

def test_geo_conversions():
    lat0, lon0 = 12.5240, 76.9000
    # Test roundtrip conversion
    x, y = latlon_to_xy(12.5260, 76.9020, lat0, lon0)
    assert x > 0 and y > 0
    lat_rt, lon_rt = xy_to_latlon(x, y, lat0, lon0)
    assert abs(lat_rt - 12.5260) < 1e-5
    assert abs(lon_rt - 76.9020) < 1e-5

    # Test haversine distance consistency
    d = haversine_distance_m(lat0, lon0, 12.5260, 76.9020)
    assert 200.0 < d < 400.0

def test_preprocess_and_indices_on_synthetic():
    img_bgr, mask, bounds, patches = generate_synthetic_field(
        scenario="mixed", seed=10, width=512, height=384
    )
    assert img_bgr.shape == (384, 512, 3)
    assert len(patches) > 0

    # Quality check
    quality, warning = check_image_quality(img_bgr)
    assert 0.0 < quality <= 1.0

    # Normalization
    normed = gray_world_normalise(img_bgr)
    assert normed.shape == img_bgr.shape

    # Canopy mask
    canopy, canopy_pct = compute_canopy_mask(normed)
    assert canopy_pct > 10.0  # Canopy detected on simulated field

    # Indices
    vari, gli, greenness = compute_vegetation_indices(normed)
    assert vari.shape == img_bgr.shape[:2]
    assert np.all(vari >= -1.0) and np.all(vari <= 1.0)

    # Render colormap
    vari_color = render_vari_colormap(vari)
    assert vari_color.shape == img_bgr.shape
