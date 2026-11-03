"""Biotic-likelihood model, recalibration, route planner, flight plans and the diagnosis schema."""

from __future__ import annotations

import itertools
import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from pydantic import ValidationError

from app.diagnosis.schema import LeafDiagnosis
from app.engine.routing import (
    MODE_SHORTEST,
    MODE_WORST_FIRST,
    Stop,
    _nearest_neighbour,
    _two_opt,
    plan_route,
    serpentine_baseline_m,
    w_pattern_m,
)
from app.engine.scoring import (
    CUE_NAMES,
    PRIOR_BIAS,
    PRIOR_WEIGHTS,
    ScoringModel,
    abiotic_hint,
    agreement,
    classify,
    confidence_level,
    confidence_of,
    normalise,
    refit,
    score_hotspot,
    sigmoid,
    tier_for,
)
from app.errors import ApiError
from app.services.flightplan import plan_flight, to_kml, to_qgc_waypoints

NEUTRAL = {
    "contrast_ratio": 1.3, "entropy_ratio": 1.12, "edge_ratio": 1.5, "irregularity": 0.2,
    "sharpness": 0.5, "log_area": 3.5, "anisotropy": 0.4,
}
PEST_LIKE = {**NEUTRAL, "contrast_ratio": 2.5, "entropy_ratio": 1.3, "edge_ratio": 4.0, "sharpness": 0.8, "log_area": 2.8, "anisotropy": 0.2}
STRIPE_LIKE = {**NEUTRAL, "contrast_ratio": 1.2, "edge_ratio": 1.3, "sharpness": 0.55, "log_area": 5.4, "anisotropy": 0.9}


class TestModel:
    def test_prior_weights_are_the_ones_in_the_trd(self):
        assert dict(zip(CUE_NAMES, PRIOR_WEIGHTS)) == {
            "contrast_ratio": 1.0, "entropy_ratio": 0.7, "edge_ratio": 0.6, "irregularity": 0.5,
            "sharpness": 0.5, "log_area": -0.6, "anisotropy": -0.8,
        }

    def test_class_boundaries(self):
        assert classify(0.65) == "likely_biotic"
        assert classify(0.64) == "uncertain"
        assert classify(0.36) == "uncertain"
        assert classify(0.35) == "likely_abiotic"

    def test_red_needs_both_evidence_and_a_strong_anomaly(self):
        assert tier_for("likely_biotic", 5.0) == "red"
        assert tier_for("likely_biotic", 2.5) == "amber"
        assert tier_for("uncertain", 9.0) == "amber"
        assert tier_for("likely_abiotic", 9.0) == "grey_blue"

    def test_cues_are_clipped_to_plus_or_minus_3(self):
        extreme = {**NEUTRAL, "contrast_ratio": 1e6, "anisotropy": -1e6}
        f = normalise(extreme)
        assert f.max() == 3.0 and f.min() == -3.0

    def test_contributions_add_up_to_the_score(self):
        model = ScoringModel.prior()
        score = score_hotspot(model, PEST_LIKE, 5.0, 8, 1.0)
        logit = sum(score.contributions.values()) + model.bias
        assert score.biotic_score == pytest.approx(float(sigmoid(logit)))

    def test_a_cue_at_its_typical_value_contributes_nothing(self):
        score = score_hotspot(ScoringModel.prior(), NEUTRAL, 3.0, 8, 1.0)
        assert all(abs(v) < 1e-9 for v in score.contributions.values())

    def test_pest_and_stripe_land_on_opposite_sides(self):
        model = ScoringModel.prior()
        pest = score_hotspot(model, PEST_LIKE, 6.0, 8, 1.0)
        stripe = score_hotspot(model, STRIPE_LIKE, 4.0, 60, 1.0)
        assert (pest.hotspot_class, pest.tier) == ("likely_biotic", "red")
        assert (stripe.hotspot_class, stripe.tier) == ("likely_abiotic", "grey_blue")
        assert stripe.abiotic_hint == "striping"
        assert pest.abiotic_hint is None

    def test_abiotic_hints(self):
        big_smooth = {**NEUTRAL, "log_area": 6.0, "anisotropy": 0.3}
        assert abiotic_hint(big_smooth, "likely_abiotic") == "large_smooth_zone"
        assert abiotic_hint(NEUTRAL, "likely_abiotic") is None
        assert abiotic_hint(big_smooth, "likely_biotic") is None


class TestConfidence:
    def test_is_the_geometric_mean_with_size_capped_at_6_tiles(self):
        assert confidence_of(0.8, 0.5, 3) == pytest.approx((0.8 * 0.5 * 0.5) ** (1 / 3))
        assert confidence_of(1.0, 1.0, 6) == confidence_of(1.0, 1.0, 600) == pytest.approx(1.0)

    def test_levels(self):
        assert confidence_level(0.7) == "high"
        assert confidence_level(0.69) == "medium"
        assert confidence_level(0.4) == "medium"
        assert confidence_level(0.39) == "low"

    def test_uncertain_never_reads_as_high_confidence(self):
        model = ScoringModel(PRIOR_WEIGHTS.copy(), 0.0)
        score = score_hotspot(model, NEUTRAL, 5.0, 20, 1.0)
        assert score.hotspot_class == "uncertain"
        assert score.confidence != "high"

    def test_poor_image_lowers_confidence(self):
        model = ScoringModel.prior()
        good = score_hotspot(model, PEST_LIKE, 5.0, 8, 1.0)
        poor = score_hotspot(model, PEST_LIKE, 5.0, 8, 0.15)
        assert poor.confidence_score < good.confidence_score


class TestRefit:
    def test_no_labels_means_the_priors(self):
        weights, bias = refit(np.empty((0, 7)), np.empty(0))
        assert np.array_equal(weights, PRIOR_WEIGHTS)
        assert bias == PRIOR_BIAS

    def test_a_biotic_label_raises_that_hotspots_score(self):
        x = normalise({**PEST_LIKE, "contrast_ratio": 1.5, "edge_ratio": 2.0})[None, :]
        before = sigmoid(x @ PRIOR_WEIGHTS + PRIOR_BIAS)[0]
        weights, bias = refit(x, np.array([1.0]))
        assert sigmoid(x @ weights + bias)[0] > before

    def test_an_abiotic_label_lowers_it(self):
        x = normalise(PEST_LIKE)[None, :]
        before = sigmoid(x @ PRIOR_WEIGHTS + PRIOR_BIAS)[0]
        weights, bias = refit(x, np.array([0.0]))
        assert sigmoid(x @ weights + bias)[0] < before

    def test_stronger_regularisation_moves_less(self):
        x = normalise(PEST_LIKE)[None, :]
        y = np.array([0.0])
        loose, _ = refit(x, y, lam=0.02)
        tight, _ = refit(x, y, lam=1.0)
        assert np.abs(tight - PRIOR_WEIGHTS).sum() < np.abs(loose - PRIOR_WEIGHTS).sum()

    def test_one_pest_label_does_not_drag_the_bias(self):
        """An unconstrained bias turned one label into 'everything looks more like pest'."""
        x = normalise(PEST_LIKE)[None, :]
        _, held = refit(x, np.array([0.0]))
        _, free = refit(x, np.array([0.0]), bias_lam=0.0)
        assert abs(held - PRIOR_BIAS) < abs(free - PRIOR_BIAS)

    def test_agreement_counts_uncertain_as_not_matching(self):
        model = ScoringModel(np.zeros(7), 0.0)  # predicts 0.5, which is uncertain, for everything
        assert agreement(model, np.zeros((2, 7)), np.array([1.0, 0.0])) == 0.0
        assert agreement(model, np.empty((0, 7)), np.empty(0)) is None


class TestRoutes:
    BASELINE = 1000.0

    def stops(self, *points, tier="red"):
        return [Stop(str(i), x, y, tier) for i, (x, y) in enumerate(points)]

    def test_baseline_on_the_demo_field_is_about_3_km(self):
        assert serpentine_baseline_m(122.9, 92.2) == pytest.approx(24 * 122.9 + 23 * 4)

    def test_w_pattern_is_four_legs_across_the_field(self):
        expected = 4 * math.hypot(122.9 / 4, 92.2) * 1.2
        assert w_pattern_m(122.9, 92.2) == pytest.approx(expected)
        assert w_pattern_m(92.2, 122.9) == pytest.approx(expected)  # orientation does not matter
        assert w_pattern_m(122.9, 92.2) < serpentine_baseline_m(122.9, 92.2) / 4

    def test_distance_includes_the_detour_factor(self):
        plan = plan_route((0, 0), self.stops((30, 40)), MODE_SHORTEST, self.BASELINE)
        assert plan.distance_m == pytest.approx(50 * 1.2)

    def test_eta_and_savings_arithmetic(self):
        plan = plan_route((0, 0), self.stops((30, 40), (60, 80)), MODE_SHORTEST, self.BASELINE)
        assert plan.distance_m == pytest.approx(120)
        assert plan.eta_min == pytest.approx(120 / 1.2 / 60 + 2 * 3)
        assert plan.saved_pct == pytest.approx(88)

    def test_speed_and_stop_time_are_editable(self):
        plan = plan_route(
            (0, 0), self.stops((60, 0)), MODE_SHORTEST, self.BASELINE, 0.0, 2.0, 10.0
        )
        assert plan.eta_min == pytest.approx(72 / 2 / 60 + 10)

    def test_saved_vs_w_pattern_can_go_negative(self):
        plan = plan_route((0, 0), self.stops((100, 0)), MODE_SHORTEST, self.BASELINE, 60.0)
        assert plan.saved_vs_w_pct < 0

    def test_two_opt_improves_on_nearest_neighbour_and_stays_close_to_optimal(self):
        """2-opt finds a local optimum, so compare it with brute force rather than expect exact."""
        rng = np.random.default_rng(3)
        improved = 0
        for _ in range(30):
            points = [tuple(p) for p in rng.uniform(0, 100, (7, 2))]
            stops = self.stops(*points)
            plan = plan_route((0, 0), stops, MODE_SHORTEST, self.BASELINE)

            def length(order):
                total, here = 0.0, (0, 0)
                for i in order:
                    total += math.dist(here, points[i])
                    here = points[i]
                return total * 1.2

            optimal = min(length(p) for p in itertools.permutations(range(7)))
            greedy = _nearest_neighbour((0, 0), points, list(range(7)))
            assert plan.distance_m <= length(greedy) + 1e-9
            assert plan.distance_m <= optimal * 1.15
            improved += plan.distance_m < length(greedy) - 1e-9
        assert improved > 0

    def test_two_opt_removes_a_crossing(self):
        # Visiting (0,10) then (10,0) then (10,10) then (0,20) crosses; 2-opt must not keep it.
        order = _two_opt((0, 0), [(0, 10), (10, 0), (10, 10), (0, 20)], [0, 2, 1, 3])
        points = [(0, 10), (10, 0), (10, 10), (0, 20)]

        def length(sequence):
            total, here = 0.0, (0, 0)
            for i in sequence:
                total += math.dist(here, points[i])
                here = points[i]
            return total

        assert length(order) < length([0, 2, 1, 3])

    def test_worst_first_visits_every_red_before_any_amber(self):
        stops = [
            Stop("a1", 1, 0, "amber"), Stop("r1", 50, 0, "red"),
            Stop("a2", 2, 0, "amber"), Stop("r2", 60, 0, "red"),
        ]
        plan = plan_route((0, 0), stops, MODE_WORST_FIRST, self.BASELINE)
        assert plan.ordered_ids[:2] == ["r1", "r2"]
        assert set(plan.ordered_ids[2:]) == {"a1", "a2"}

    def test_shortest_is_never_longer_than_worst_first(self):
        rng = np.random.default_rng(1)
        stops = [
            Stop(str(i), float(x), float(y), "red" if i % 2 else "amber")
            for i, (x, y) in enumerate(rng.uniform(0, 100, (12, 2)))
        ]
        short = plan_route((0, 0), stops, MODE_SHORTEST, self.BASELINE)
        worst = plan_route((0, 0), stops, MODE_WORST_FIRST, self.BASELINE)
        assert short.distance_m <= worst.distance_m + 1e-9

    def test_no_stops_means_no_walk(self):
        plan = plan_route((0, 0), [], MODE_SHORTEST, self.BASELINE)
        assert plan.ordered_ids == []
        assert plan.distance_m == 0 and plan.eta_min == 0
        assert plan.saved_pct == 100

    def test_unknown_mode_is_rejected(self):
        with pytest.raises(ValueError):
            plan_route((0, 0), [], "scenic", self.BASELINE)


SQUARE = [(12.5225, 76.8945), (12.5225, 76.8957), (12.5237, 76.8957), (12.5237, 76.8945)]


class TestFlightPlan:
    def test_default_camera_matches_the_trd_example(self):
        plan = plan_flight(SQUARE, 35, 0.75, 0.65)
        assert plan["summary"]["gsd_cm"] == pytest.approx(1.2, abs=0.1)
        assert plan["summary"]["footprint_width_m"] == pytest.approx(50, abs=2)

    def test_waypoints_stay_inside_the_polygon_and_alternate_direction(self):
        plan = plan_flight(SQUARE, 35, 0.75, 0.65)
        waypoints = plan["waypoints"]
        assert len(waypoints) == 2 * plan["summary"]["flight_lines"]
        lats = [w["lat"] for w in waypoints]
        assert min(lats) >= 12.5225 - 1e-6 and max(lats) <= 12.5237 + 1e-6
        first_leg = waypoints[1]["lon"] - waypoints[0]["lon"]
        second_leg = waypoints[3]["lon"] - waypoints[2]["lon"]
        assert first_leg * second_leg < 0 or (
            (waypoints[1]["lat"] - waypoints[0]["lat"])
            * (waypoints[3]["lat"] - waypoints[2]["lat"]) < 0
        )

    def test_more_overlap_means_more_lines(self):
        low = plan_flight(SQUARE, 35, 0.5, 0.3)["summary"]
        high = plan_flight(SQUARE, 35, 0.85, 0.8)["summary"]
        assert high["flight_lines"] > low["flight_lines"]
        assert high["estimated_photos"] > low["estimated_photos"]

    def test_rejects_altitude_over_the_ceiling(self):
        with pytest.raises(ApiError) as caught:
            plan_flight(SQUARE, 150, 0.75, 0.65)
        assert caught.value.code == "altitude_too_high"

    def test_rejects_a_self_crossing_outline(self):
        bowtie = [SQUARE[0], SQUARE[2], SQUARE[1], SQUARE[3]]
        with pytest.raises(ApiError) as caught:
            plan_flight(bowtie, 35, 0.75, 0.65)
        assert caught.value.code == "invalid_polygon"

    def test_exports_are_valid(self):
        plan = plan_flight(SQUARE, 35, 0.75, 0.65)
        kml = to_kml("A & B", plan["waypoints"])
        root = ET.fromstring(kml)  # also proves the name was escaped
        assert root.tag.endswith("kml")

        rows = to_qgc_waypoints(plan["waypoints"], 9.0).strip().split("\n")
        assert rows[0] == "QGC WPL 110"
        parsed = [row.split("\t") for row in rows[1:]]
        assert all(len(row) == 12 for row in parsed)
        assert [int(row[0]) for row in parsed] == list(range(len(parsed)))
        commands = [row[3] for row in parsed]
        assert commands[1] == "22"  # takeoff
        assert commands[2] == "206"  # camera trigger on
        assert commands[-1] == "20"  # return to launch


def diagnosis(**overrides) -> dict:
    return {
        "plant_visible": True,
        "image_quality": "good",
        "observed_symptoms": ["chewed margins"],
        "candidates": [{"name": "Caterpillar", "type": "pest", "probability": 0.6}],
        "confirm_by": ["Check underside"],
        "actions_ipm": ["Remove affected leaves"],
        "needs_expert": False,
        "language": "en",
        **overrides,
    }


class TestDiagnosisSchema:
    def test_accepts_the_shape_in_the_trd(self):
        LeafDiagnosis(**diagnosis())

    def test_rejects_probabilities_over_one(self):
        with pytest.raises(ValidationError):
            LeafDiagnosis(
                **diagnosis(
                    candidates=[
                        {"name": "A", "type": "pest", "probability": 0.7},
                        {"name": "B", "type": "disease", "probability": 0.5},
                    ]
                )
            )

    def test_rejects_an_out_of_range_probability_and_unknown_type(self):
        with pytest.raises(ValidationError):
            LeafDiagnosis(**diagnosis(candidates=[{"name": "A", "type": "pest", "probability": 1.5}]))
        with pytest.raises(ValidationError):
            LeafDiagnosis(**diagnosis(candidates=[{"name": "A", "type": "alien", "probability": 0.5}]))

    def test_keeps_the_top_three_candidates_sorted(self):
        result = LeafDiagnosis(
            **diagnosis(
                candidates=[
                    {"name": "D", "type": "pest", "probability": 0.1},
                    {"name": "A", "type": "pest", "probability": 0.4},
                    {"name": "C", "type": "pest", "probability": 0.15},
                    {"name": "B", "type": "pest", "probability": 0.3},
                ]
            )
        )
        assert [c.name for c in result.candidates] == ["A", "B", "C"]

    @pytest.mark.parametrize(
        "text",
        ["Spray 2 ml per litre", "Apply 500 g per acre", "Use a 0.5% solution", "Mix 10 kg"],
    )
    def test_strips_actions_that_give_a_dose(self, text):
        result = LeafDiagnosis(**diagnosis(actions_ipm=[text, "Remove affected leaves"]))
        assert result.actions_ipm == ["Remove affected leaves"]

    def test_keeps_actions_with_harmless_numbers(self):
        action = "Check 5 neighbouring plants"
        assert LeafDiagnosis(**diagnosis(actions_ipm=[action])).actions_ipm == [action]
