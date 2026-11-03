"""The analysis engine: geometry, texture, anomaly, clustering and the simulator."""

from __future__ import annotations

import json
import math

import cv2
import numpy as np
import pytest
from skimage.feature import graycomatrix, graycoprops

from app.engine.geo import Bounds, FieldFrame, bounds_from_centre, gsd_for_flight
from app.engine.hotspots import anomaly_scores, cluster_hotspots, robust_z
from app.engine.pipeline import AnalysisParams, analyze
from app.engine.preprocess import (
    _odd_px,
    canopy_mask,
    compute_indices,
    gray_world,
    nodata_mask,
    quality_check,
    resample_to_working,
)
from app.engine.scoring import ScoringModel
from app.engine.simulator import (
    CLASS_DISTRACTOR,
    CLASS_DROUGHT,
    CLASS_NUTRIENT,
    CLASS_PEST,
    SimConfig,
    save,
    simulate,
)
from app.engine.tiles import TileGrid, compute_tiles, glcm_features


@pytest.fixture(scope="module")
def full_field():
    """The full demo canvas, which has room for every kind of stress and distractor."""
    return simulate(SimConfig("mixed", "medium", 10))


@pytest.fixture(scope="module")
def result(small_sim):
    return analyze(small_sim.image, small_sim.bounds, AnalysisParams(), ScoringModel.prior())


class TestGeometry:
    def test_uses_the_flat_earth_formula_from_the_trd(self):
        bounds = Bounds(12.0, 76.0, 12.001, 76.001)
        frame = FieldFrame(bounds, 100, 100)
        expected_width = 0.001 * 111_320 * math.cos(math.radians(12.0005))
        assert frame.width_m == pytest.approx(expected_width)
        assert frame.height_m == pytest.approx(0.001 * 110_574)

    def test_latlon_and_pixel_round_trips(self):
        frame = FieldFrame(bounds_from_centre(12.5, 76.9, 120, 90), 4000, 3000)
        lat, lon = frame.xy_to_latlon(13.0, -22.0)
        assert frame.latlon_to_xy(lat, lon) == pytest.approx((13.0, -22.0))
        x, y = frame.px_to_xy(321, 654)
        assert frame.xy_to_px(x, y) == pytest.approx((321, 654))

    def test_image_top_left_is_the_north_west_corner(self):
        bounds = bounds_from_centre(12.5, 76.9, 120, 90)
        frame = FieldFrame(bounds, 4000, 3000)
        lat, lon = frame.xy_to_latlon(*frame.px_to_xy(0, 0))
        assert lat == pytest.approx(bounds.ne_lat)
        assert lon == pytest.approx(bounds.sw_lon)

    def test_gsd_matches_the_trd_example(self):
        # A 12 MP consumer drone at 35 m: about 1.2 cm per pixel, about 50 m across.
        gsd = gsd_for_flight(6.3, 35, 4.5, 4000)
        assert gsd == pytest.approx(0.012, abs=0.001)
        assert gsd * 4000 == pytest.approx(50, abs=2)


class TestResampling:
    def test_downsamples_to_about_3_cm(self):
        rgb = np.zeros((1000, 2000, 3), np.uint8)
        out, scale = resample_to_working(rgb, 0.012)
        assert scale == pytest.approx(0.4)
        assert out.shape[1] == 800

    def test_never_upsamples(self):
        rgb = np.zeros((100, 200, 3), np.uint8)
        out, scale = resample_to_working(rgb, 0.05)
        assert scale == 1.0
        assert out.shape == rgb.shape

    def test_caps_the_long_edge(self):
        rgb = np.zeros((10, 8000, 3), np.uint8)
        out, _ = resample_to_working(rgb, 0.03)
        assert max(out.shape[:2]) <= 4096


class TestGlcm:
    """The vectorised GLCM must agree with scikit-image, which the TRD names."""

    @pytest.fixture
    def image(self):
        rng = np.random.default_rng(0)
        rows = (np.sin(np.arange(96) / 3)[:, None] * 40 + 128).repeat(144, axis=1)
        return np.clip(rows + rng.normal(0, 25, (96, 144)), 0, 255).astype(np.uint8)

    def test_matches_scikit_image_per_tile(self, image):
        t, levels = 48, 16
        ours = glcm_features(image, np.ones(image.shape, bool), t, levels)
        angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
        for row in range(image.shape[0] // t):
            for col in range(image.shape[1] // t):
                tile = (image[row * t : (row + 1) * t, col * t : (col + 1) * t] // 16).astype(
                    np.uint8
                )
                p = graycomatrix(tile, [1, 3], angles, levels, symmetric=True, normed=True)
                for prop in ("contrast", "homogeneity", "energy"):
                    assert ours[prop][row, col] == pytest.approx(
                        graycoprops(p, prop).mean(), rel=1e-6
                    )
                logged = np.where(p > 0, np.log2(np.where(p > 0, p, 1)), 0)
                entropy = -(p * logged).sum(axis=(0, 1)).mean()
                assert ours["entropy"][row, col] == pytest.approx(entropy, rel=1e-6)
                contrast = graycoprops(p, "contrast")
                c0, c90 = contrast[:, 0].mean(), contrast[:, 2].mean()
                assert ours["anisotropy"][row, col] == pytest.approx(
                    abs(c0 - c90) / (c0 + c90), rel=1e-6
                )

    def test_ignores_pairs_outside_the_canopy(self):
        # A sharp soil edge inside a tile must not raise contrast when the soil is masked out.
        image = np.full((48, 48), 100, np.uint8)
        image[:, 24:] = 240
        mask = np.zeros(image.shape, bool)
        mask[:, :24] = True
        assert glcm_features(image, mask, 48)["contrast"][0, 0] == pytest.approx(0.0)


class TestPreprocess:
    def test_blur_is_flagged(self, small_sim):
        assert quality_check(small_sim.image).warnings == []
        blurred = quality_check(cv2.GaussianBlur(small_sim.image, (0, 0), 3))
        assert any("blurry" in w for w in blurred.warnings)

    def test_bad_exposure_is_flagged(self, small_sim):
        report = quality_check(np.clip(small_sim.image.astype(int) + 200, 0, 255).astype(np.uint8))
        assert any("bright or too dark" in w for w in report.warnings)

    def test_damped_white_balance_keeps_stressed_canopy(self, full_field):
        """Full gray-world pushes mean ExG to zero and masks out the stress we need to score."""
        mask = canopy_mask(gray_world(full_field.image)).mask
        for cls in (CLASS_DROUGHT, CLASS_NUTRIENT, CLASS_PEST):
            assert mask[full_field.mask == cls].mean() > 0.9

        full = canopy_mask(gray_world(full_field.image, strength=1.0)).mask
        assert full[full_field.mask == CLASS_DROUGHT].mean() < 0.5

    def test_soil_is_excluded(self, full_field):
        mask = canopy_mask(gray_world(full_field.image)).mask
        assert mask[full_field.mask == CLASS_DISTRACTOR].mean() < 0.35

    def test_a_field_of_bare_soil_is_not_read_as_canopy(self):
        """With no green mode to find, Otsu lands in the noise and can pass everything."""
        rng = np.random.default_rng(0)
        soil = np.clip(rng.normal((140, 105, 80), 6, (480, 640, 3)), 0, 255).astype(np.uint8)
        result = canopy_mask(gray_world(soil))
        assert result.exg_threshold >= 0.0
        assert result.canopy_pct < 5

    def test_kernels_are_defined_in_metres(self):
        assert _odd_px(0.75, 0.03) == 25
        assert _odd_px(0.75, 0.1146) == 7
        assert _odd_px(0.15, 0.1146) == 3


class TestNoData:
    """Real orthomosaics have large empty margins, unlike anything the simulator produces."""

    @pytest.fixture
    def with_margin(self, small_sim):
        rgb = small_sim.image.copy()
        rgb[:, : rgb.shape[1] // 2] = 0
        return rgb

    def test_margin_is_detected_and_dark_specks_are_not(self, with_margin):
        rgb = with_margin.copy()
        rgb[100:104, -100:-96] = 0  # a small dark gap inside the crop
        nodata = nodata_mask(rgb)
        assert nodata[:, : rgb.shape[1] // 2 - 10].all()
        assert not nodata[100:104, -100:-96].any()

    def test_survives_jpeg_ringing(self, with_margin):
        ok, buffer = cv2.imencode(".jpg", with_margin, [cv2.IMWRITE_JPEG_QUALITY, 90])
        assert ok
        nodata = nodata_mask(cv2.imdecode(buffer, cv2.IMREAD_COLOR))
        assert nodata[:, : with_margin.shape[1] // 2 - 10].mean() > 0.99

    def test_margin_does_not_trigger_exposure_warning(self, with_margin):
        assert quality_check(with_margin).clipped_share > 0.4
        report = quality_check(with_margin, nodata_mask(with_margin))
        assert report.clipped_share < 0.01
        assert report.warnings == []

    def test_margin_does_not_skew_white_balance_or_shadows(self, small_sim, with_margin):
        nodata = nodata_mask(with_margin)
        result = canopy_mask(gray_world(with_margin, nodata=nodata), nodata=nodata)
        assert result.data_fraction == pytest.approx(0.5, abs=0.02)
        assert result.shadow_pct < 10
        assert result.canopy_pct > 85  # measured on the field half alone
        assert not result.mask[nodata].any()

    def test_pipeline_reports_margin_tiles_separately(self, small_sim, with_margin):
        result = analyze(with_margin, small_sim.bounds, AnalysisParams(), ScoringModel.prior())
        assert result.canopy.data_fraction == pytest.approx(0.5, abs=0.02)
        assert (result.grid.nodata_frac >= 0.5).mean() == pytest.approx(0.5, abs=0.05)
        assert not any("too dark" in w for w in result.quality.warnings)


class TestAnomaly:
    def test_robust_z_formula(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
        valid = np.ones(5, bool)
        # median 3, MAD 1
        assert robust_z(x, valid)[1] == pytest.approx(-1 / 1.4826)
        assert robust_z(x, valid)[4] == pytest.approx(97 / 1.4826)

    def test_outlier_does_not_move_the_baseline(self):
        valid = np.ones(5, bool)
        a = robust_z(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), valid)[1]
        b = robust_z(np.array([1.0, 2.0, 3.0, 4.0, 5000.0]), valid)[1]
        assert a == pytest.approx(b)

    def test_anomaly_formula_and_excluded_tiles(self):
        zeros = np.zeros((1, 6))
        grid = TileGrid(
            tile_px=48, ny=1, nx=6,
            canopy_frac=zeros + 1, nodata_frac=zeros,
            valid=np.array([[True, True, True, True, True, False]]),
            green_mean=np.array([[0.0, 1.0, 2.0, 3.0, 4.0, -99.0]]),
            green_std=zeros, hue_shift=zeros,
            contrast=np.array([[2.0, 2.0, 2.0, 2.0, 2.0, 2.0]]),
            homogeneity=zeros, energy=zeros, entropy=zeros, anisotropy=zeros, edge_density=zeros,
        )
        score = anomaly_scores(grid)
        assert score[0, 0] == pytest.approx(2 / 1.4826)  # median 2, MAD 1
        assert score[0, 4] == 0  # greener than typical is not an anomaly
        assert score[0, 5] == 0  # excluded, however low its greenness


class TestPipeline:
    def test_finds_every_pest_patch_of_4_m2_or_more(self, small_sim, result):
        t = result.params.tile_px
        covered = np.zeros(small_sim.mask.shape, bool)
        for item in result.hotspots:
            for r, c in zip(item.draft.rows, item.draft.cols):
                covered[r * t : (r + 1) * t, c * t : (c + 1) * t] = True
        patches = [
            p for p in small_sim.patches if p["class"] == "pest" and p["area_m2"] >= 4
        ]
        assert patches
        for patch in patches:
            cx, cy = patch["center_px"]
            assert covered[max(0, cy - 40) : cy + 40, max(0, cx - 40) : cx + 40].any(), patch

    def test_hotspots_are_polygons_with_areas_and_seven_cues(self, result):
        assert result.hotspots
        for item in result.hotspots:
            assert item.draft.polygon.geom_type == "Polygon"
            assert item.draft.polygon.is_valid
            assert item.draft.area_m2 >= result.params.min_cluster_m2
            assert len(item.draft.cues) == 7
            assert all(math.isfinite(v) for v in item.draft.cues.values())

    def test_reports_every_stage_timing_except_route(self, result):
        assert set(result.timings) == {
            "quality_check", "canopy_mask", "indices", "texture", "anomalies", "clustering",
            "scoring",
        }

    def test_raising_the_threshold_flags_fewer_tiles(self, result):
        flagged = []
        for tau in (1.5, 2.0, 3.0, 5.0, 8.0):
            _, mask = cluster_hotspots(
                result.grid, result.frame, result.anomaly, tau, 1.6, 3, 2.0, result.gradient
            )
            flagged.append(int(mask.sum()))
        assert flagged == sorted(flagged, reverse=True)
        assert flagged[0] > flagged[-1]

    def test_corner_touching_tiles_still_give_one_polygon(self, result):
        grid = result.grid
        forced = np.zeros_like(result.anomaly)
        # Four scorable tiles in a diagonal line, touching only at their corners.
        start = next(
            (r, c)
            for r in range(grid.ny - 3)
            for c in range(grid.nx - 3)
            if all(grid.valid[r + i, c + i] for i in range(4))
        )
        for i in range(4):
            forced[start[0] + i, start[1] + i] = 9.0
        drafts, _ = cluster_hotspots(
            grid, result.frame, forced, 2.0, 1.6, 3, 2.0, result.gradient
        )
        assert len(drafts) == 1
        assert drafts[0].polygon.geom_type == "Polygon"

    def test_cancel_stops_between_stages(self, small_sim):
        from app.engine.pipeline import Cancelled

        calls = {"n": 0}

        def cancel_on_third() -> bool:
            calls["n"] += 1
            return calls["n"] >= 3

        with pytest.raises(Cancelled):
            analyze(
                small_sim.image, small_sim.bounds, AnalysisParams(), ScoringModel.prior(),
                should_cancel=cancel_on_third,
            )

    @staticmethod
    def young_crop(row_height_px: int) -> tuple[np.ndarray, Bounds]:
        """Bare soil with green rows 1.2 m apart, which is what an early-season field looks like."""
        rng = np.random.default_rng(0)
        rgb = rng.normal((140, 105, 80), 6, (960, 1280, 3))
        for y in range(0, 960, 40):
            rgb[y : y + row_height_px, :] = rng.normal((60, 130, 50), 6, (row_height_px, 1280, 3))
        bounds = bounds_from_centre(12.5, 76.9, 1280 * 0.03, 960 * 0.03)
        return np.clip(rgb, 0, 255).astype(np.uint8), bounds

    def test_warns_when_little_of_the_field_can_be_scored(self):
        rgb, bounds = self.young_crop(8)
        scored = analyze(rgb, bounds, AnalysisParams(), ScoringModel.prior())
        assert any("enough green canopy" in w for w in scored.quality.warnings)

    def test_lower_canopy_cutoff_scores_more_tiles(self):
        rgb, bounds = self.young_crop(14)
        strict = analyze(rgb, bounds, AnalysisParams(min_canopy=0.6), ScoringModel.prior())
        loose = analyze(rgb, bounds, AnalysisParams(min_canopy=0.2), ScoringModel.prior())
        assert loose.grid.valid.sum() > strict.grid.valid.sum()


class TestSimulator:
    def test_same_seed_gives_the_same_field(self):
        a = simulate(SimConfig("mixed", "medium", 5, width=512, height=384))
        b = simulate(SimConfig("mixed", "medium", 5, width=512, height=384))
        assert np.array_equal(a.image, b.image)

    def test_different_seeds_differ(self):
        a = simulate(SimConfig("mixed", "medium", 5, width=512, height=384))
        b = simulate(SimConfig("mixed", "medium", 6, width=512, height=384))
        assert not np.array_equal(a.image, b.image)

    def test_full_canvas_matches_the_spec(self):
        sim = simulate(SimConfig("mixed", "medium", 10))
        assert sim.image.shape == (3072, 4096, 3)
        frame = FieldFrame(sim.bounds, 4096, 3072)
        assert frame.width_m == pytest.approx(122.9, abs=0.5)
        assert frame.height_m == pytest.approx(92.2, abs=0.5)
        kinds = {p["class"] for p in sim.patches}
        assert {"pest", "drought", "nutrient", "distractor"} <= kinds
        distractors = {p.get("kind") for p in sim.patches}
        assert {"soil_track", "tree_shadow", "water_trough"} <= distractors

    def test_healthy_has_no_stress(self):
        sim = simulate(SimConfig("healthy", "medium", 5, width=1024, height=768))
        for cls in (CLASS_PEST, CLASS_DROUGHT, CLASS_NUTRIENT):
            assert not (sim.mask == cls).any()

    def test_one_command_writes_image_mask_bounds_and_patches(self, tmp_path):
        sim = simulate(SimConfig("pest", "easy", 2, width=512, height=384))
        paths = save(sim, tmp_path)
        assert all(path.exists() for path in paths.values())
        meta = json.loads(paths["patches"].read_text())
        assert meta["synthetic"] is True
        assert set(json.loads(paths["bounds"].read_text())) == {
            "sw_lat", "sw_lon", "ne_lat", "ne_lon",
        }

    def test_compute_tiles_rejects_an_image_smaller_than_a_tile(self):
        small = np.zeros((10, 10, 3), np.float32)
        layers = compute_indices(small, np.ones((10, 10), bool))
        with pytest.raises(ValueError, match="smaller than one"):
            compute_tiles(small, np.ones((10, 10), bool), layers.greenness)
