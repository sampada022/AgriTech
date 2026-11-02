import os
import json
import math
import random
import argparse
import cv2
import numpy as np
from PIL import Image

# Mandya, Karnataka coordinates baseline
DEFAULT_ORIGIN_LAT = 12.5240
DEFAULT_ORIGIN_LON = 76.9000

def generate_synthetic_field(
    scenario: str = "mixed",
    seed: int = 42,
    difficulty: str = "medium",
    width: int = 2048,
    height: int = 1536,
    gsd_cm: float = 3.0
):
    """
    Generates a realistic synthetic drone crop orthomosaic with ground truth masks:
    - Crop rows with sinusoidal sway
    - Pest patches: noise-warped boundary, speckle thinning, yellow-brown discoloration
    - Drought zones: smooth low-frequency yellowing, soft edges
    - Nutrient stripes: bands along row direction
    - Distractors: bare soil access tracks, tree shadows
    """
    random.seed(seed)
    np.random.seed(seed)

    # 1. Base Soil Background (Warm sandy-clay brown)
    img = np.zeros((height, width, 3), dtype=np.float32)
    img[:, :, 0] = 55.0 + np.random.normal(0, 5, (height, width))  # B
    img[:, :, 1] = 85.0 + np.random.normal(0, 6, (height, width))  # G
    img[:, :, 2] = 110.0 + np.random.normal(0, 8, (height, width)) # R

    # Ground truth class mask: 0=healthy, 1=pest, 2=drought, 3=nutrient, 4=distractor
    gt_mask = np.zeros((height, width), dtype=np.uint8)
    patches_meta = []

    # 2. Crop Rows (Sugarcane / Maize pattern)
    # Row spacing ~ 0.8m @ 3cm/px = ~26 px
    row_spacing = 26
    y_coords, x_coords = np.indices((height, width))
    row_wave = np.sin((y_coords / 40.0) + (x_coords / 80.0)) * 4.0
    row_phase = (x_coords + row_wave) % row_spacing
    crop_canopy = (row_phase < 18).astype(np.float32)

    # Green crop color: Vibrant green (B: 35, G: 145, R: 60)
    for c, val in enumerate([35.0, 145.0, 60.0]):
        img[:, :, c] = np.where(
            crop_canopy > 0,
            val + np.random.normal(0, 12, (height, width)),
            img[:, :, c]
        )

    # 3. Distractor: Bare Soil Field Track & Road
    track_center = width // 2
    track_mask = (abs(x_coords - track_center - (np.sin(y_coords / 100.0) * 15)) < 30)
    for c, val in enumerate([70.0, 95.0, 125.0]):
        img[track_mask, c] = val + np.random.normal(0, 5, np.sum(track_mask))
    gt_mask[track_mask] = 4

    # 4. Nutrient Deficiency (Bands along rows)
    if scenario in ["mixed", "healthy"]:
        stripe_y = height // 4
        nutrient_band = (abs(y_coords - stripe_y) < 60) & (crop_canopy > 0)
        img[nutrient_band, 0] += 15.0  # Slightly yellowed
        img[nutrient_band, 1] -= 20.0
        img[nutrient_band, 2] += 45.0
        gt_mask[nutrient_band] = 3

    # 5. Drought Zone (Broad low-frequency smooth gradient)
    if scenario in ["mixed", "healthy"]:
        d_center_x = int(width * 0.75)
        d_center_y = int(height * 0.65)
        d_dist = np.sqrt((x_coords - d_center_x)**2 + (y_coords - d_center_y)**2)
        drought_mask = (d_dist < 220) & (crop_canopy > 0)
        soft_fade = np.clip(1.0 - (d_dist[drought_mask] / 220.0), 0, 1)
        
        img[drought_mask, 0] += 10.0 * soft_fade
        img[drought_mask, 1] -= 25.0 * soft_fade
        img[drought_mask, 2] += 50.0 * soft_fade
        gt_mask[drought_mask] = 2

    # 6. Pest Patches (Ragged, speckled, high-contrast lesions)
    if scenario in ["pest", "mixed"]:
        num_patches = random.randint(4, 7) if difficulty != "easy" else 3
        for i in range(num_patches):
            # Center coordinates avoiding edges
            px = random.randint(180, width - 180)
            py = random.randint(150, height - 150)
            radius = random.randint(40, 80)

            dist = np.sqrt((x_coords - px)**2 + (y_coords - py)**2)
            noise = np.random.normal(0, 10, (height, width))
            pest_region = ((dist + noise) < radius) & (crop_canopy > 0)

            if np.sum(pest_region) > 50:
                speckle = np.random.rand(*img.shape[:2]) < 0.65
                affected = pest_region & speckle

                # Brown-yellow chlorosis & necrotic chewed tissue
                img[affected, 0] = 30.0 + np.random.normal(0, 8, np.sum(affected)) # B
                img[affected, 1] = 75.0 + np.random.normal(0, 10, np.sum(affected)) # G
                img[affected, 2] = 115.0 + np.random.normal(0, 12, np.sum(affected)) # R
                gt_mask[pest_region] = 1

                area_m2 = round(float(np.sum(pest_region)) * ((gsd_cm / 100.0) ** 2), 2)
                patches_meta.append({
                    "id": f"patch_{i+1}",
                    "type": "pest",
                    "center_px": [px, py],
                    "radius_px": radius,
                    "area_m2": area_m2
                })

    final_bgr = np.clip(img, 0, 255).astype(np.uint8)

    # Compute bounding box in Mandya, Karnataka
    field_width_m = width * (gsd_cm / 100.0)
    field_height_m = height * (gsd_cm / 100.0)
    lat_span = field_height_m / 110574.0
    lon_span = field_width_m / (111320.0 * math.cos(math.radians(DEFAULT_ORIGIN_LAT)))

    bounds = {
        "sw": [DEFAULT_ORIGIN_LAT - lat_span/2.0, DEFAULT_ORIGIN_LON - lon_span/2.0],
        "ne": [DEFAULT_ORIGIN_LAT + lat_span/2.0, DEFAULT_ORIGIN_LON + lon_span/2.0]
    }

    return final_bgr, gt_mask, bounds, patches_meta

def main():
    parser = argparse.ArgumentParser(description="AeroScout Synthetic Field Generator")
    parser.add_argument("--scenario", choices=["healthy", "pest", "mixed"], default="mixed")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    parser.add_argument("--outdir", default="demo/scenarios/mixed")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    img, mask, bounds, patches = generate_synthetic_field(
        scenario=args.scenario,
        seed=args.seed,
        difficulty=args.difficulty
    )

    cv2.imwrite(os.path.join(args.outdir, "field.jpg"), img)
    cv2.imwrite(os.path.join(args.outdir, "ground_truth_mask.png"), mask * 50)
    
    with open(os.path.join(args.outdir, "bounds.json"), "w") as f:
        json.dump(bounds, f, indent=2)

    with open(os.path.join(args.outdir, "patches.json"), "w") as f:
        json.dump(patches, f, indent=2)

    print(f"Synthetic field scenario '{args.scenario}' generated successfully in {args.outdir}.")

if __name__ == "__main__":
    main()

