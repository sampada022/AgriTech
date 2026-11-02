import pytest
from app.model.calibrate import refit_logistic_model
from app.model.versions import record_feedback_and_recalibrate, TRAINING_SAMPLES
from app.mock_data import INITIAL_WEIGHTS, INITIAL_BIAS, MOCK_MODEL_STATE, MOCK_HOTSPOTS

def test_numpy_logistic_gradient_descent():
    weights = INITIAL_WEIGHTS.copy()
    bias = INITIAL_BIAS
    priors = INITIAL_WEIGHTS.copy()

    training_data = [
        {"cues": {"contrast_ratio": 2.4, "entropy_ratio": 1.8, "edge_ratio": 2.0, "irregularity": 0.4, "sharpness": 0.8, "log_area": 2.2, "anisotropy": 0.05}, "label": 1},
        {"cues": {"contrast_ratio": 2.1, "entropy_ratio": 1.6, "edge_ratio": 1.7, "irregularity": 0.35, "sharpness": 0.7, "log_area": 2.5, "anisotropy": 0.08}, "label": 1},
        {"cues": {"contrast_ratio": 0.8, "entropy_ratio": 0.9, "edge_ratio": 0.7, "irregularity": 0.1, "sharpness": 0.2, "log_area": 4.1, "anisotropy": 0.75}, "label": 0},
        {"cues": {"contrast_ratio": 0.9, "entropy_ratio": 1.0, "edge_ratio": 0.8, "irregularity": 0.15, "sharpness": 0.3, "log_area": 3.8, "anisotropy": 0.65}, "label": 0}
    ]

    new_w, new_b, agreement = refit_logistic_model(
        current_weights=weights,
        current_bias=bias,
        prior_weights=priors,
        training_data=training_data,
        lambda_reg=0.1,
        epochs=40
    )

    # Agreement on training set should be >= 75%
    assert agreement >= 75.0
    assert "contrast_ratio" in new_w

def test_closed_loop_feedback_recalibration():
    # Clear training samples for isolated test
    TRAINING_SAMPLES.clear()
    MOCK_MODEL_STATE["active_version"] = "v1"
    MOCK_MODEL_STATE["n_labels"] = 0
    MOCK_MODEL_STATE["history"] = [
        {"version": "v1", "n_labels": 0, "training_agreement_pct": None, "created_at": "2026-11-02T10:00:00Z"}
    ]

    assert "s_01" in MOCK_HOTSPOTS
    assert len(MOCK_HOTSPOTS["s_01"]) > 0

    # Confirm ground truth label on h_01 as "pest"
    res = record_feedback_and_recalibrate(hotspot_id="h_01", label_str="pest")
    assert res["model_version"] == "v2"
    assert res["n_labels"] == 1
    assert MOCK_MODEL_STATE["active_version"] == "v2"

    # Verify h_01 status updated to confirmed
    h01 = next(h for h in MOCK_HOTSPOTS["s_01"] if h["id"] == "h_01")
    assert h01["properties"]["status"] == "confirmed"

    # Verify remaining unlabelled spots were re-scored live
    h04_updated = next(h for h in MOCK_HOTSPOTS["s_01"] if h["id"] == "h_04")
    assert "biotic_score" in h04_updated["properties"]
