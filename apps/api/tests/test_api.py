"""The HTTP contract, end to end: the closed loop the frontend builds against."""

from __future__ import annotations

import io
import json
import zipfile

import numpy as np
import pytest
from PIL import Image, JpegImagePlugin

from app.config import get_settings
from app.diagnosis import service as diagnosis_service
from app.diagnosis.providers import DiagnosisUnavailable
from app.diagnosis.schema import LeafDiagnosis
from app.engine.render import OVERLAY_BYTE_BUDGET
from app.services.demo_settings import demo_settings
from app.storage import field_image_path, public_dir
from tests.conftest import jpeg_bytes, leaf_photo, upload_field, wait_for_scan


def assert_error_shape(response, status: int, code: str | None = None) -> None:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert set(error) == {"code", "message", "hint"}
    assert error["message"]
    if code:
        assert error["code"] == code


def post_photo(client, hotspot_id, seed=1, **form):
    return client.post(
        f"/api/hotspots/{hotspot_id}/observations",
        files={"photo": ("leaf.jpg", leaf_photo(seed), "image/jpeg")},
        data=form,
    )


def hotspots_of(client, scan_id):
    return client.get(f"/api/scans/{scan_id}/hotspots").json()["features"]


@pytest.fixture
def live_reply(monkeypatch):
    """A provider that succeeds, standing in for the LLM."""
    calls = []

    class Provider:
        name = "stub"

        def diagnose(self, image, context):
            calls.append(context)
            return LeafDiagnosis(
                plant_visible=True,
                image_quality="good",
                observed_symptoms=["Chewed margins"],
                candidates=[{"name": "Caterpillar", "type": "pest", "probability": 0.7}],
                confirm_by=["Check underside"],
                actions_ipm=["Remove affected leaves"],
                needs_expert=False,
                language=context.language,
            )

    monkeypatch.setattr(diagnosis_service, "_provider", lambda: Provider())
    return calls


class TestFields:
    def test_upload_creates_a_field_card(self, client, small_sim):
        response = upload_field(client, small_sim.image, small_sim.bounds)
        assert response.status_code == 201
        field = response.json()
        assert field["data_source_badge"] == "Synthetic data"
        assert field["bounds"]["leaflet"] == [
            [field["bounds"]["sw_lat"], field["bounds"]["sw_lon"]],
            [field["bounds"]["ne_lat"], field["bounds"]["ne_lon"]],
        ]
        assert field["gsd_cm"] == pytest.approx(3.0, abs=0.05)
        assert field["latest_scan"] is None
        assert client.get(field["thumbnail_url"]).status_code == 200
        listed = client.get("/api/fields").json()
        assert [f["id"] for f in listed] == [field["id"]]

    def test_stand_in_imagery_gets_its_own_badge(self, client, small_sim):
        field = upload_field(client, small_sim.image, small_sim.bounds, data_source="stand_in")
        assert field.json()["data_source_badge"] == "Real pixels, stand-in field"

    def test_rejects_a_non_image_with_an_image_extension(self, client, small_sim):
        bounds = small_sim.bounds.as_dict()
        response = client.post(
            "/api/fields",
            files={"image": ("field.jpg", b"not an image at all", "image/jpeg")},
            data={"name": "x", **bounds},
        )
        assert_error_shape(response, 422, "invalid_image")

    def test_rejects_a_format_outside_the_allowed_list(self, client, small_sim):
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64)).save(buffer, "GIF")
        response = client.post(
            "/api/fields",
            files={"image": ("field.gif", buffer.getvalue(), "image/gif")},
            data={"name": "x", **small_sim.bounds.as_dict()},
        )
        assert_error_shape(response, 422, "invalid_image")

    def test_accepts_tiff_orthomosaics_and_turns_alpha_into_no_data(self, client, small_sim):
        rgba = np.dstack((small_sim.image, np.full(small_sim.image.shape[:2], 255, np.uint8)))
        rgba[:, :400, 3] = 0
        rgba[:, :400, :3] = 200  # colour under transparency must not leak through
        buffer = io.BytesIO()
        Image.fromarray(rgba).save(buffer, "TIFF")
        field = client.post(
            "/api/fields",
            files={"image": ("ortho.tif", buffer.getvalue(), "image/tiff")},
            data={"name": "Ortho", "data_source": "stand_in", **small_sim.bounds.as_dict()},
        )
        assert field.status_code == 201, field.text
        started = client.post(f"/api/fields/{field.json()['id']}/scans", json={}).json()
        scan = wait_for_scan(client, started["id"])
        assert scan["status"] == "done"
        assert scan["grid"]["data_fraction"] < 0.8
        assert scan["grid"]["tiles_nodata"] > 0
        # Percentages are of the field itself, not of its bounding box.
        assert scan["kpis"]["field_area_m2"] < 0.8 * (1536 * 0.03 * 1152 * 0.03)

    @pytest.mark.parametrize(
        "bad",
        [
            {"ne_lat": 11.0},  # north of the south-west corner it is not
            {"ne_lon": 70.0},
            {"sw_lat": 95.0},
            {"ne_lat": 13.5},  # about 100 km tall, well past the flat-earth limit
        ],
    )
    def test_rejects_bad_bounds(self, client, small_sim, bad):
        form = {"name": "x", **small_sim.bounds.as_dict(), **bad}
        response = client.post(
            "/api/fields",
            files={"image": ("f.jpg", jpeg_bytes(small_sim.image[:64, :64]), "image/jpeg")},
            data=form,
        )
        assert_error_shape(response, 422, "invalid_bounds")

    def test_rejects_oversized_uploads(self, client, small_sim, monkeypatch):
        monkeypatch.setattr(get_settings(), "max_field_image_mb", 0)
        response = upload_field(client, small_sim.image[:64, :64], small_sim.bounds)
        assert_error_shape(response, 413, "file_too_large")

    def test_rejects_too_many_pixels(self, client, small_sim, monkeypatch):
        monkeypatch.setattr(get_settings(), "max_field_pixels", 100)
        response = upload_field(client, small_sim.image[:64, :64], small_sim.bounds)
        assert_error_shape(response, 413, "image_too_large")

    def test_stored_image_loses_exif_gps(self, client, small_sim):
        exif = Image.Exif()
        exif[0x010F] = "SecretDroneMaker"
        data = jpeg_bytes(small_sim.image[:256, :256], exif=exif)
        assert b"SecretDroneMaker" in data
        field = client.post(
            "/api/fields",
            files={"image": ("f.jpg", data, "image/jpeg")},
            data={"name": "x", **small_sim.bounds.as_dict()},
        ).json()
        assert b"SecretDroneMaker" not in field_image_path(field["id"]).read_bytes()

    def test_stored_image_keeps_full_colour_resolution(self, client, small_sim):
        """The canopy mask works from colour, and 4:2:0 subsampling changes what it finds."""
        field = upload_field(client, small_sim.image[:256, :256], small_sim.bounds).json()
        with Image.open(field_image_path(field["id"])) as stored:
            assert JpegImagePlugin.get_sampling(stored) == 0  # 4:4:4


class TestScans:
    def test_analysis_runs_and_reports_all_stages(self, client, scanned_field):
        _, scan = scanned_field
        assert scan["progress"] == 100
        assert len(scan["stages"]) == 8
        assert set(scan["stage_timings"]) == set(scan["stages"])
        assert scan["elapsed_s"] > 0
        assert scan["quality"]["score"] > 0
        assert scan["canopy_pct"] > 50
        assert scan["model_version_used"] == 1
        assert client.get(scan["mask_preview_url"]).status_code == 200

    def test_layers_are_served_under_the_byte_budget(self, client, scanned_field):
        _, scan = scanned_field
        for layer in ("rgb", "vari", "heat"):
            body = client.get(f"/api/scans/{scan['id']}/layers/{layer}")
            assert body.status_code == 200
            info = body.json()
            assert info["bytes"] <= OVERLAY_BYTE_BUDGET
            assert info["bounds"]["leaflet"]
            image = client.get(info["url"])
            assert image.status_code == 200
            assert image.headers["content-type"] == "image/webp"
            assert len(image.content) == info["bytes"]

    def test_hotspot_contract_matches_the_trd(self, client, scanned_field):
        _, scan = scanned_field
        collection = client.get(f"/api/scans/{scan['id']}/hotspots").json()
        assert collection["type"] == "FeatureCollection"
        features = collection["features"]
        assert features
        assert [f["properties"]["rank"] for f in features] == list(range(1, len(features) + 1))
        for feature in features:
            assert feature["type"] == "Feature"
            assert feature["id"].startswith("h_")
            ring = feature["geometry"]["coordinates"][0]
            assert feature["geometry"]["type"] == "Polygon"
            assert ring[0] == ring[-1]
            lon, lat = ring[0]
            assert 76 < lon < 78 and 12 < lat < 13  # [lon, lat], in the right order
            props = feature["properties"]
            # Every key in the TRD 7.2 example must be present under the same name.
            for key in (
                "scan_id", "rank", "area_m2", "tier", "biotic_score", "class", "confidence",
                "cues", "contributions", "status", "manual", "crop_url",
            ):
                assert key in props, key
            assert set(props["cues"]) == {
                "contrast_ratio", "entropy_ratio", "edge_ratio", "irregularity", "sharpness",
                "log_area", "anisotropy",
            }
            assert props["tier"] in ("red", "amber", "grey_blue")
            assert props["status"] == "detected"
            assert client.get(props["crop_url"]).status_code == 200

    def test_kpis_show_both_walk_baselines_and_assumptions(self, scanned_field):
        _, scan = scanned_field
        kpis = scan["kpis"]
        for key in (
            "hotspot_count", "tier_counts", "area_flagged_pct", "spray_area_pct",
            "walk_saved_pct", "walk_saved_vs_w_pattern_pct", "w_pattern_distance_m",
        ):
            assert kpis[key] is not None, key
        notes = kpis["assumptions"]["notes"]
        assert "not a pesticide saving" in notes["spray_area"]
        assert "W-pattern" in notes["walk_saved_vs_w_pattern"]

    def test_low_canopy_cutoff_is_accepted_and_recorded(self, client, small_sim):
        field = upload_field(client, small_sim.image, small_sim.bounds).json()
        started = client.post(f"/api/fields/{field['id']}/scans", json={"min_canopy": 0.3}).json()
        scan = wait_for_scan(client, started["id"])
        assert scan["params"]["min_canopy"] == 0.3

    def test_invalid_params_use_the_error_shape(self, client, small_sim):
        field = upload_field(client, small_sim.image, small_sim.bounds).json()
        response = client.post(f"/api/fields/{field['id']}/scans", json={"tile_px": 3})
        assert_error_shape(response, 422, "invalid_request")

    def test_a_field_too_small_to_tile_fails_with_a_message_not_a_crash(self, client, small_sim):
        field = upload_field(client, small_sim.image[:32, :32], small_sim.bounds).json()
        started = client.post(f"/api/fields/{field['id']}/scans", json={}).json()
        scan = wait_for_scan(client, started["id"])
        assert scan["status"] == "failed"
        assert "smaller than one" in scan["error"]["message"]

    def test_cancelling_a_queued_scan(self, client, small_sim):
        field = upload_field(client, small_sim.image, small_sim.bounds).json()
        first = client.post(f"/api/fields/{field['id']}/scans", json={}).json()
        second = client.post(f"/api/fields/{field['id']}/scans", json={}).json()
        client.post(f"/api/scans/{second['id']}/cancel")
        assert wait_for_scan(client, second["id"])["status"] == "cancelled"
        assert wait_for_scan(client, first["id"])["status"] == "done"

    def test_missing_things_are_404s_in_the_error_shape(self, client):
        assert_error_shape(client.get("/api/scans/nope"), 404, "scan_not_found")
        assert_error_shape(client.get("/api/fields/nope"), 404, "field_not_found")
        assert_error_shape(client.get("/api/hotspots/nope"), 404, "hotspot_not_found")
        assert_error_shape(client.get("/api/nothing/here"), 404)


class TestRoutes:
    def test_plan_and_read_back(self, client, scanned_field):
        _, scan = scanned_field
        route = client.post(f"/api/scans/{scan['id']}/route", json={"mode": "worst_first"}).json()
        assert route["mode"] == "worst_first"
        assert route["stop_count"] == len(route["stops"])
        assert client.get(f"/api/scans/{scan['id']}/route").json()["id"] == route["id"]
        assert route["polyline"]["type"] == "LineString"
        assert len(route["polyline"]["coordinates"]) == route["stop_count"] + 1
        tiers = [s["tier"] for s in route["stops"]]
        assert "grey_blue" not in tiers
        assert tiers == sorted(tiers, key=lambda t: {"red": 0, "amber": 1}[t])
        assert route["baseline_m"] > 0 and route["w_pattern_m"] > 0

    def test_include_abiotic_adds_grey_stops(self, client, scanned_field):
        _, scan = scanned_field
        grey = sum(
            f["properties"]["tier"] == "grey_blue" for f in hotspots_of(client, scan["id"])
        )
        without = client.post(f"/api/scans/{scan['id']}/route", json={}).json()
        with_grey = client.post(
            f"/api/scans/{scan['id']}/route", json={"include_abiotic": True}
        ).json()
        assert with_grey["stop_count"] == without["stop_count"] + grey

    def test_start_too_far_away_is_rejected(self, client, scanned_field):
        _, scan = scanned_field
        response = client.post(
            f"/api/scans/{scan['id']}/route", json={"start": {"lat": 40.0, "lon": -74.0}}
        )
        assert_error_shape(response, 422, "start_too_far")


class TestThresholdSlider:
    def test_higher_threshold_flags_less_and_keeps_ids_of_worked_on_hotspots(
        self, client, scanned_field
    ):
        _, scan = scanned_field
        features = hotspots_of(client, scan["id"])
        worked_on = features[0]["id"]
        client.patch(f"/api/hotspots/{worked_on}", json={"status": "inspected"})
        before = client.get(f"/api/scans/{scan['id']}").json()["grid"]["tiles_flagged"]

        result = client.post(f"/api/scans/{scan['id']}/threshold", json={"threshold": 6.0}).json()
        assert result["scan"]["params"]["threshold"] == 6.0
        assert result["scan"]["grid"]["tiles_flagged"] < before
        assert worked_on in {f["id"] for f in result["hotspots"]["features"]}
        ranks = [f["properties"]["rank"] for f in result["hotspots"]["features"]]
        assert ranks == list(range(1, len(ranks) + 1))
        assert result["route"] is not None

    def test_new_clusters_never_overlap_kept_hotspots(self, client, scanned_field):
        from shapely.geometry import shape

        _, scan = scanned_field
        worked_on = hotspots_of(client, scan["id"])[0]["id"]
        client.patch(f"/api/hotspots/{worked_on}", json={"status": "inspected"})
        features = client.post(
            f"/api/scans/{scan['id']}/threshold", json={"threshold": 1.5}
        ).json()["hotspots"]["features"]
        kept = next(f for f in features if f["id"] == worked_on)
        for feature in features:
            if feature["id"] != worked_on:
                assert not shape(kept["geometry"]).intersects(shape(feature["geometry"]))

    def test_needs_a_finished_scan(self, client, small_sim):
        field = upload_field(client, small_sim.image, small_sim.bounds).json()
        started = client.post(f"/api/fields/{field['id']}/scans", json={}).json()
        client.post(f"/api/scans/{started['id']}/cancel")
        wait_for_scan(client, started["id"])
        response = client.post(f"/api/scans/{started['id']}/threshold", json={"threshold": 3})
        if client.get(f"/api/scans/{started['id']}").json()["status"] != "done":
            assert_error_shape(response, 409, "scan_not_ready")


class TestManualHotspots:
    def test_added_hotspot_is_scored_and_joins_the_ranking(self, client, scanned_field, small_sim):
        _, scan = scanned_field
        bounds = small_sim.bounds
        lat, lon = (bounds.sw_lat + bounds.ne_lat) / 2, (bounds.sw_lon + bounds.ne_lon) / 2
        count = len(hotspots_of(client, scan["id"]))
        response = client.post(
            f"/api/scans/{scan['id']}/hotspots",
            json={"lat": lat, "lon": lon, "radius_m": 2.5, "note": "Saw caterpillars"},
        )
        assert response.status_code == 201, response.text
        feature = response.json()
        assert feature["properties"]["manual"] is True
        assert feature["properties"]["note"] == "Saw caterpillars"
        assert feature["properties"]["area_m2"] == pytest.approx(np.pi * 2.5**2, rel=0.05)
        assert len(hotspots_of(client, scan["id"])) == count + 1

    def test_outside_the_field_is_rejected(self, client, scanned_field):
        _, scan = scanned_field
        response = client.post(
            f"/api/scans/{scan['id']}/hotspots", json={"lat": 13.0, "lon": 77.5, "radius_m": 2}
        )
        assert_error_shape(response, 422, "outside_field")


class TestDiagnosis:
    def test_live_reply_is_stored_and_marks_the_hotspot_inspected(
        self, client, scanned_field, live_reply
    ):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        response = post_photo(client, target, lat=12.5, lon=76.9, language="en")
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["diagnosis"]["source"] == "live"
        assert body["diagnosis"]["suggested_label"] == "pest"
        assert body["diagnosis"]["result"]["candidates"][0]["name"] == "Caterpillar"
        assert "product label" in body["diagnosis"]["advisory"]
        assert {o["label"] for o in body["diagnosis"]["label_options"]} == {
            "pest", "disease", "nutrient", "water", "weeds_other", "false_alarm",
        }
        assert client.get(body["photo_url"]).status_code == 200
        detail = client.get(f"/api/hotspots/{target}").json()
        assert detail["feature"]["properties"]["status"] == "inspected"
        assert [o["id"] for o in detail["observations"]] == [body["id"]]

    def test_aerial_hint_reaches_the_provider_as_context(self, client, scanned_field, live_reply):
        _, scan = scanned_field
        feature = hotspots_of(client, scan["id"])[0]
        post_photo(client, feature["id"], language="kn")
        context = live_reply[0]
        assert context.crop == "Maize"
        assert context.language == "kn"
        assert context.aerial_class == feature["properties"]["class"]

    def test_same_photo_hits_the_cache_and_skips_the_provider(
        self, client, scanned_field, live_reply
    ):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        assert post_photo(client, target).json()["diagnosis"]["source"] == "live"
        assert post_photo(client, target).json()["diagnosis"]["source"] == "cache"
        assert len(live_reply) == 1
        # A different language is a different reply, so it must not reuse the cached one.
        assert post_photo(client, target, language="kn").json()["diagnosis"]["source"] == "live"

    def test_a_rehearsed_photo_survives_a_reset_and_an_api_outage(
        self, client, small_sim, monkeypatch
    ):
        """Reset before judging, then lose the API: the real reply must still come back."""
        replies = []

        class Live:
            name = "live"

            def diagnose(self, image, context):
                replies.append(context)
                return LeafDiagnosis(
                    plant_visible=True,
                    image_quality="good",
                    observed_symptoms=["Chewed margins"],
                    candidates=[{"name": "Rehearsed reply", "type": "pest", "probability": 0.7}],
                    confirm_by=[],
                    actions_ipm=[],
                    needs_expert=False,
                    language=context.language,
                )

        class Down:
            name = "down"

            def diagnose(self, image, context):
                raise DiagnosisUnavailable("connection")

        def first_hotspot():
            client.post("/api/demo/load/mixed")
            return hotspots_of(client, "s_mixed")[0]["id"]

        monkeypatch.setattr(diagnosis_service, "_provider", lambda: Live())
        assert post_photo(client, first_hotspot()).json()["diagnosis"]["source"] == "live"

        client.post("/api/demo/reset")
        monkeypatch.setattr(diagnosis_service, "_provider", lambda: Down())
        diagnosis = post_photo(client, first_hotspot()).json()["diagnosis"]
        assert diagnosis["source"] == "cache"
        assert diagnosis["result"]["candidates"][0]["name"] == "Rehearsed reply"
        assert len(replies) == 1

    def test_replies_outside_demo_mode_are_not_kept_past_a_reset(
        self, client, scanned_field, live_reply, monkeypatch
    ):
        monkeypatch.setattr(get_settings(), "demo_mode", False)
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        post_photo(client, target)
        assert not list(diagnosis_service.demo_replies_dir().glob("*.json"))

    def test_provider_failure_in_demo_mode_gives_a_labelled_stand_in(
        self, client, scanned_field, monkeypatch
    ):
        class Broken:
            name = "broken"

            def diagnose(self, image, context):
                raise DiagnosisUnavailable("timeout")

        monkeypatch.setattr(diagnosis_service, "_provider", lambda: Broken())
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        diagnosis = post_photo(client, target).json()["diagnosis"]
        assert diagnosis["source"] == "canned"
        assert diagnosis["result"]["candidates"]

    def test_provider_failure_outside_demo_mode_gives_the_fallback_card(
        self, client, scanned_field, monkeypatch
    ):
        class Broken:
            name = "broken"

            def diagnose(self, image, context):
                raise RuntimeError("something unexpected")

        monkeypatch.setattr(diagnosis_service, "_provider", lambda: Broken())
        monkeypatch.setattr(get_settings(), "demo_mode", False)
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        response = post_photo(client, target)
        assert response.status_code == 201
        diagnosis = response.json()["diagnosis"]
        assert diagnosis["source"] == "fallback"
        assert diagnosis["result"] is None
        assert diagnosis["message"] == "Could not analyse, choose a cause yourself."
        assert len(diagnosis["label_options"]) == 6

    def test_the_fallback_card_is_translated(self, client, scanned_field, monkeypatch):
        monkeypatch.setattr(diagnosis_service, "_provider", lambda: None)
        monkeypatch.setattr(get_settings(), "demo_mode", False)
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        diagnosis = post_photo(client, target, language="kn").json()["diagnosis"]
        assert diagnosis["message"] != "Could not analyse, choose a cause yourself."
        assert diagnosis["label_options"][0]["name"] == "ಕೀಟ ಹಾನಿ"

    def test_force_cached_ai_skips_the_live_call(self, client, scanned_field, live_reply):
        client.patch("/api/demo/settings", json={"force_cached_ai": True})
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        assert post_photo(client, target).json()["diagnosis"]["source"] == "canned"
        assert live_reply == []

    def test_canned_replies_follow_the_requested_language(self, client, scanned_field):
        client.patch("/api/demo/settings", json={"force_cached_ai": True})
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        result = post_photo(client, target, language="kn").json()["diagnosis"]["result"]
        assert result["language"] == "kn"
        assert not result["candidates"][0]["name"].isascii()

    def test_photo_is_rate_limited_per_client(self, client, scanned_field, monkeypatch):
        monkeypatch.setattr(get_settings(), "diagnosis_rate_limit_per_min", 2)
        diagnosis_service.rate_limiter.reset()
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        assert post_photo(client, target).status_code == 201
        assert post_photo(client, target).status_code == 201
        assert_error_shape(post_photo(client, target), 429, "rate_limited")
        diagnosis_service.rate_limiter.reset()

    def test_rejects_a_non_image_photo(self, client, scanned_field):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        response = client.post(
            f"/api/hotspots/{target}/observations",
            files={"photo": ("leaf.jpg", b"nope", "image/jpeg")},
        )
        assert_error_shape(response, 422, "invalid_image")

    def test_rejects_an_unknown_language(self, client, scanned_field):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        assert post_photo(client, target, language="fr").status_code == 422

    def test_served_photo_has_no_exif_and_is_downsized(self, client, scanned_field):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        exif = Image.Exif()
        exif[0x010F] = "SecretPhone"
        pixels = (np.random.default_rng(0).random((1600, 2000, 3)) * 255).astype(np.uint8)
        data = jpeg_bytes(pixels, exif=exif)
        assert b"SecretPhone" in data
        body = client.post(
            f"/api/hotspots/{target}/observations",
            files={"photo": ("leaf.jpg", data, "image/jpeg")},
            data={"lat": 12.5, "lon": 76.9},
        ).json()
        served = client.get(body["photo_url"]).content
        assert b"SecretPhone" not in served
        assert max(Image.open(io.BytesIO(served)).size) <= 1280
        # The GPS we deliberately keep is still on the observation.
        assert (body["lat"], body["lon"]) == (12.5, 76.9)

    def test_blurry_photo_gets_a_warning_but_still_a_reply(self, client, scanned_field):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        flat = np.full((400, 400, 3), 120, np.uint8)
        body = client.post(
            f"/api/hotspots/{target}/observations",
            files={"photo": ("leaf.jpg", jpeg_bytes(flat), "image/jpeg")},
        ).json()
        assert "blurry" in body["diagnosis"]["photo_warning"]


class TestClosedLoop:
    def observe(self, client, hotspot_id, seed=1):
        return post_photo(client, hotspot_id, seed=seed).json()["id"]

    def test_confirm_refits_rescores_and_replans(self, client, scanned_field):
        _, scan = scanned_field
        features = hotspots_of(client, scan["id"])
        target = features[0]["id"]
        response = client.post(
            f"/api/observations/{self.observe(client, target)}/confirm", json={"label": "pest"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["model"]["version"] == 2
        assert body["model"]["previous_version"] == 1
        assert body["model"]["changed"] is True
        assert body["model"]["label_count"] == 1
        assert "nudge" in body["model"]["note"]
        assert set(body["model"]["weight_changes"]) == set(features[0]["properties"]["cues"])
        assert target not in {s["hotspot_id"] for s in body["route"]["stops"]}
        assert "product label" in body["guidance"]["advisory"]
        assert body["guidance"]["label_name"] == "Pest damage"

        updated = {f["id"]: f["properties"] for f in hotspots_of(client, scan["id"])}
        assert updated[target]["status"] == "confirmed"
        assert updated[target]["label"] == "pest"
        assert updated[target]["rank"] == len(updated)  # resolved hotspots sink to the bottom
        versions = client.get("/api/model/history").json()["versions"]
        assert [v["version"] for v in versions] == [2, 1]
        assert client.get("/api/model").json()["version"] == 2
        assert client.get(f"/api/scans/{scan['id']}").json()["model_version_used"] == 2

    def test_labels_map_to_the_right_side_of_the_model(self, client, scanned_field):
        _, scan = scanned_field
        features = hotspots_of(client, scan["id"])
        before = {f["id"]: f["properties"]["biotic_score"] for f in features}
        abiotic = features[0]["id"]
        client.post(
            f"/api/observations/{self.observe(client, abiotic)}/confirm", json={"label": "water"}
        )
        detail = client.get(f"/api/hotspots/{abiotic}").json()["feature"]["properties"]
        assert detail["tier"] == "grey_blue"
        # The prediction stays on record, which is what agreement is measured against.
        assert detail["biotic_score"] == before[abiotic]

    def test_false_alarm_clears_without_training(self, client, scanned_field):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        body = client.post(
            f"/api/observations/{self.observe(client, target)}/confirm",
            json={"label": "false_alarm"},
        ).json()
        assert body["model"]["version"] == 1
        assert body["model"]["changed"] is False
        assert body["false_positive"]["count"] == 1
        props = client.get(f"/api/hotspots/{target}").json()["feature"]["properties"]
        assert props["status"] == "cleared"

    def test_three_false_alarms_suggest_raising_the_threshold(self, client, scanned_field):
        _, scan = scanned_field
        threshold_before = client.get(f"/api/scans/{scan['id']}").json()["params"]["threshold"]
        last = None
        for index, feature in enumerate(hotspots_of(client, scan["id"])[:3]):
            last = client.post(
                f"/api/observations/{self.observe(client, feature['id'], index)}/confirm",
                json={"label": "false_alarm"},
            ).json()
        assert last["false_positive"]["suggest_raise_threshold"] is True
        # A hint, not an action.
        assert client.get(f"/api/scans/{scan['id']}").json()["params"]["threshold"] == threshold_before

    def test_confirming_the_same_label_twice_does_not_bump_the_version(
        self, client, scanned_field
    ):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        observation = self.observe(client, target)
        client.post(f"/api/observations/{observation}/confirm", json={"label": "pest"})
        again = client.post(f"/api/observations/{observation}/confirm", json={"label": "pest"})
        assert again.json()["model"]["version"] == 2
        changed = client.post(f"/api/observations/{observation}/confirm", json={"label": "water"})
        assert changed.json()["model"]["version"] == 3
        assert changed.json()["model"]["label_count"] == 1

    def test_unknown_label_is_rejected(self, client, scanned_field):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        response = client.post(
            f"/api/observations/{self.observe(client, target)}/confirm", json={"label": "aliens"}
        )
        assert_error_shape(response, 422, "invalid_request")

    def test_model_reset_returns_to_priors_and_retires_labels_from_training(
        self, client, scanned_field
    ):
        _, scan = scanned_field
        features = hotspots_of(client, scan["id"])
        client.post(
            f"/api/observations/{self.observe(client, features[0]['id'])}/confirm",
            json={"label": "pest"},
        )
        reset = client.post("/api/model/reset").json()
        assert reset["version"] == 1
        assert reset["is_prior"] is True
        assert [v["version"] for v in client.get("/api/model/history").json()["versions"]] == [1]
        # The old label stays visible, but the next refit starts from scratch without it.
        next_label = client.post(
            f"/api/observations/{self.observe(client, features[1]['id'], 2)}/confirm",
            json={"label": "pest"},
        ).json()
        assert next_label["model"]["version"] == 2
        assert next_label["model"]["label_count"] == 1
        props = client.get(f"/api/hotspots/{features[0]['id']}").json()["feature"]["properties"]
        assert props["label"] == "pest"

    def test_status_workflow(self, client, scanned_field):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        for status in ("assigned", "inspected", "confirmed", "cleared", "detected"):
            response = client.patch(f"/api/hotspots/{target}", json={"status": status})
            assert response.json()["properties"]["status"] == status
        noted = client.patch(f"/api/hotspots/{target}", json={"note": "Check again Friday"})
        assert noted.json()["properties"]["note"] == "Check again Friday"
        invalid = client.patch(f"/api/hotspots/{target}", json={"status": "archived"})
        assert_error_shape(invalid, 422, "invalid_request")

    def test_clearing_a_stop_removes_it_from_the_route(self, client, scanned_field):
        _, scan = scanned_field
        route = client.get(f"/api/scans/{scan['id']}/route").json()
        if not route["stops"]:
            pytest.skip("No routed stops in this field.")
        stop = route["stops"][0]["hotspot_id"]
        client.patch(f"/api/hotspots/{stop}", json={"status": "cleared"})
        after = client.get(f"/api/scans/{scan['id']}/route").json()
        assert stop not in {s["hotspot_id"] for s in after["stops"]}


class TestDemoControls:
    def test_all_three_scenarios_load_with_results_ready(self, client):
        for scenario in ("healthy", "pest", "mixed"):
            loaded = client.post(f"/api/demo/load/{scenario}")
            assert loaded.status_code == 200, loaded.text
            body = loaded.json()
            assert body["synthetic"] is True
            scan = client.get(f"/api/scans/{body['scan_id']}").json()
            assert scan["status"] == "done"
            assert scan["data_source_badge"] == "Synthetic data"
            assert scan["kpis"]["walk_saved_pct"] is not None
            for info in scan["layers"].values():
                assert client.get(info["url"]).status_code == 200
        # Cached scenarios must load in under a second (TRD 8.4), now that assets are built.
        assert client.post("/api/demo/load/mixed").json()["load_seconds"] < 1.0

    def test_mixed_demo_lifts_uncertain_pests_with_one_label(self, client):
        """The on-stage moment from TRD 6.7. This guards it against scoring changes."""
        client.post("/api/demo/load/mixed")
        features = hotspots_of(client, "s_mixed")
        amber = [f for f in features if f["properties"]["tier"] == "amber"]
        assert len(amber) >= 2
        target = amber[0]["id"]
        observation = post_photo(client, target).json()["id"]
        body = client.post(
            f"/api/observations/{observation}/confirm", json={"label": "pest"}
        ).json()
        assert body["model"]["version"] == 2
        climbs = [
            c for c in body["changes"]
            if c["hotspot_id"] != target and c["before"]["tier"] != c["after"]["tier"]
        ]
        lifted = [c for c in climbs if (c["before"]["tier"], c["after"]["tier"]) == ("amber", "red")]
        assert lifted, "One label should lift at least one uncertain pest patch into red."
        # Nothing should climb out of the informational tier on the strength of one label.
        assert not [c for c in climbs if c["before"]["tier"] == "grey_blue"]

    def test_healthy_demo_is_quiet(self, client):
        client.post("/api/demo/load/healthy")
        tiers = client.get("/api/scans/s_healthy").json()["kpis"]["tier_counts"]
        assert tiers["red"] == 0
        assert tiers["amber"] <= 1

    def test_reloading_a_scenario_gives_a_fresh_copy(self, client):
        client.post("/api/demo/load/mixed")
        target = hotspots_of(client, "s_mixed")[0]["id"]
        post_photo(client, target)
        assert client.get(f"/api/hotspots/{target}").json()["observations"]
        client.post("/api/demo/load/mixed")
        assert client.get(f"/api/hotspots/{target}").json()["observations"] == []

    def test_loaded_scenario_supports_the_slider_and_manual_hotspots(self, client):
        client.post("/api/demo/load/pest")
        assert client.post("/api/scans/s_pest/threshold", json={"threshold": 3}).status_code == 200

    def test_reloading_removes_labels_from_hand_started_scans_too(self, client):
        """Left behind, they would keep counting toward the false-positive hint."""
        client.post("/api/demo/load/mixed")
        started = client.post("/api/fields/f_mixed/scans", json={}).json()
        wait_for_scan(client, started["id"])
        target = hotspots_of(client, started["id"])[0]["id"]
        observation = post_photo(client, target).json()["id"]
        confirmed = client.post(
            f"/api/observations/{observation}/confirm", json={"label": "false_alarm"}
        ).json()
        assert confirmed["false_positive"]["count"] == 1

        client.post("/api/demo/load/mixed")
        assert client.get(f"/api/observations/{observation}").status_code == 404
        assert client.get("/api/model").json()["false_positive"]["count"] == 0
        assert client.get(f"/api/scans/{started['id']}").status_code == 404

    def test_unknown_scenario_is_a_404(self, client):
        assert_error_shape(client.post("/api/demo/load/mars"), 404, "scenario_not_found")

    def test_reset_deletes_everything(self, client, scanned_field):
        field, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        photo = post_photo(client, target).json()["photo_url"]
        assert client.get(photo).status_code == 200
        client.patch("/api/demo/settings", json={"force_cached_ai": True, "sim_speed_mps": 3})
        assert client.post("/api/demo/reset").status_code == 200
        assert client.get("/api/fields").json() == []
        assert client.get(f"/api/fields/{field['id']}").status_code == 404
        assert client.get(photo).status_code == 404
        assert client.get("/api/model").json()["version"] == 1
        settings = client.get("/api/demo/settings").json()
        assert settings == {"force_cached_ai": False, "sim_speed_mps": 1.5}

    def test_settings_validate(self, client):
        assert_error_shape(
            client.patch("/api/demo/settings", json={"sim_speed_mps": -1}), 422, "invalid_request"
        )

    def test_demo_routes_are_off_unless_enabled(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "demo_mode", False)
        assert_error_shape(client.post("/api/demo/reset"), 404, "demo_mode_off")
        assert_error_shape(client.post("/api/demo/load/mixed"), 404, "demo_mode_off")
        assert_error_shape(client.get("/api/demo/settings"), 404, "demo_mode_off")
        monkeypatch.setattr(demo_settings, "force_cached_ai", False)


class TestExports:
    def test_geojson_and_csv(self, client, scanned_field):
        _, scan = scanned_field
        geojson = client.get(f"/api/scans/{scan['id']}/export/geojson")
        assert geojson.status_code == 200
        assert 'attachment; filename="' in geojson.headers["content-disposition"]
        assert json.loads(geojson.content)["type"] == "FeatureCollection"
        csv_text = client.get(f"/api/scans/{scan['id']}/export/csv").text
        assert csv_text.splitlines()[0].startswith("rank,hotspot_id")

    def test_csv_neutralises_spreadsheet_formulas(self, client, scanned_field):
        _, scan = scanned_field
        target = hotspots_of(client, scan["id"])[0]["id"]
        client.patch(f"/api/hotspots/{target}", json={"note": '=HYPERLINK("http://evil")'})
        assert "'=HYPERLINK" in client.get(f"/api/scans/{scan['id']}/export/csv").text

    def test_dataset_zip_has_labels_features_and_photos(self, client, scanned_field):
        _, scan = scanned_field
        features = hotspots_of(client, scan["id"])
        observation = post_photo(client, features[0]["id"]).json()["id"]
        client.post(f"/api/observations/{observation}/confirm", json={"label": "pest"})
        # An unlabelled photo is not part of the dataset.
        post_photo(client, features[1]["id"], seed=2)
        archive = zipfile.ZipFile(
            io.BytesIO(client.get(f"/api/scans/{scan['id']}/export/dataset.zip").content)
        )
        names = archive.namelist()
        assert {"labels.csv", "features.csv", "README.txt", f"photos/{observation}.jpg"} <= set(names)
        assert len([n for n in names if n.startswith("photos/")]) == 1
        assert "pest" in archive.read("labels.csv").decode()
        assert features[0]["id"] in archive.read("features.csv").decode()

    def test_unknown_export_kind_is_rejected(self, client, scanned_field):
        _, scan = scanned_field
        assert client.get(f"/api/scans/{scan['id']}/export/pdf").status_code == 422


class TestFlightPlans:
    POLYGON = [
        {"lat": 12.5225, "lon": 76.8945}, {"lat": 12.5225, "lon": 76.8957},
        {"lat": 12.5237, "lon": 76.8957}, {"lat": 12.5237, "lon": 76.8945},
    ]

    def test_create_and_download(self, client):
        response = client.post("/api/flightplans", json={"polygon": self.POLYGON})
        assert response.status_code == 201, response.text
        plan = response.json()
        assert plan["altitude_m"] == 35
        assert plan["waypoints"]
        assert "Line of sight" in plan["summary"]["safety"] or "line of sight" in plan["summary"]["safety"]
        assert client.get(plan["kml_url"]).text.startswith("<?xml")
        assert client.get(plan["waypoint_file_url"]).text.startswith("QGC WPL 110")

    def test_too_high_is_rejected(self, client):
        response = client.post(
            "/api/flightplans", json={"polygon": self.POLYGON, "altitude_m": 500}
        )
        assert_error_shape(response, 422, "altitude_too_high")


class TestPlumbing:
    def test_health_reports_dependencies(self, client):
        body = client.get("/api/health").json()
        assert body["status"] == "ok"
        assert body["database"] is True
        assert body["demo_mode"] is True
        assert {"provider", "model", "api_key_set", "reachable"} <= set(body["llm"])
        assert "reachable" in body["basemap"]

    def test_the_api_key_is_never_exposed(self, client, monkeypatch):
        monkeypatch.setattr(get_settings(), "anthropic_api_key", "sk-ant-super-secret")
        assert "super-secret" not in client.get("/api/health").text
        assert "super-secret" not in client.get("/openapi.json").text

    def test_cors_allows_known_origins_only(self, client):
        allowed = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
        blocked = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in blocked.headers

    def test_files_revalidate_so_a_rebuilt_overlay_is_never_stale(self, client, scanned_field):
        _, scan = scanned_field
        url = scan["layers"]["rgb"]["url"]
        first = client.get(url)
        assert first.headers["cache-control"] == "no-cache"
        again = client.get(url, headers={"If-None-Match": first.headers["etag"]})
        assert again.status_code == 304

    def test_private_files_are_not_served(self, client, scanned_field):
        field, scan = scanned_field
        assert client.get(f"/files/../private/fields/{field['id']}.jpg").status_code == 404
        assert client.get(f"/files/%2e%2e/private/fields/{field['id']}.jpg").status_code == 404
        assert client.get(f"/files/private/scans/{scan['id']}/cache.npz").status_code == 404
        assert (public_dir() / scan["id"]).exists()

    def test_validation_endpoint_needs_benchmark_results(self, client, tmp_path, monkeypatch):
        assert_error_shape(client.get("/api/model/validation"), 404, "benchmark_missing")
        results = tmp_path / "r.json"
        results.write_text(json.dumps({"synthetic": True, "disclaimer": "x", "levels": []}))
        real = tmp_path / "real.json"
        real.write_text(json.dumps({"sugarcane": {"canopy_pct": 38.7}}))
        monkeypatch.setattr(get_settings(), "benchmark_results", results)
        monkeypatch.setattr(get_settings(), "real_pixel_results", real)
        body = client.get("/api/model/validation").json()
        assert body["synthetic"] is True
        assert body["real_pixels"]["checks"]["sugarcane"]["canopy_pct"] == 38.7
        assert "no pest ground truth" in body["real_pixels"]["disclaimer"]

    def test_openapi_documents_the_contract(self, client):
        paths = client.get("/openapi.json").json()["paths"]
        for path in (
            "/api/fields", "/api/fields/{field_id}/scans", "/api/scans/{scan_id}",
            "/api/scans/{scan_id}/hotspots", "/api/hotspots/{hotspot_id}",
            "/api/scans/{scan_id}/route", "/api/hotspots/{hotspot_id}/observations",
            "/api/observations/{observation_id}/confirm", "/api/model", "/api/model/history",
            "/api/model/reset", "/api/scans/{scan_id}/export/{kind}", "/api/flightplans",
            "/api/demo/load/{scenario}", "/api/demo/reset", "/api/health",
        ):
            assert path in paths, path
