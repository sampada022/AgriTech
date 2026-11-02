from fastapi import APIRouter
from app.mock_data import MOCK_MODEL_STATE, MOCK_OBSERVATIONS, MOCK_HOTSPOTS, INITIAL_WEIGHTS, INITIAL_BIAS

router = APIRouter(prefix="/demo", tags=["Demo Controls"])

@router.post("/load/{scenario}")
def load_scenario(scenario: str):
    # Returns loaded demo confirmation
    return {
        "status": "loaded",
        "scenario": scenario,
        "scan_id": "s_01",
        "field_id": "f_mandya_01",
        "message": f"Precomputed scenario '{scenario}' loaded successfully."
    }

@router.post("/reset")
def reset_demo():
    from app.model.versions import TRAINING_SAMPLES
    MOCK_OBSERVATIONS.clear()
    TRAINING_SAMPLES.clear()
    MOCK_MODEL_STATE["active_version"] = "v1"
    MOCK_MODEL_STATE["n_labels"] = 0
    MOCK_MODEL_STATE["training_agreement_pct"] = None
    MOCK_MODEL_STATE["weights"] = INITIAL_WEIGHTS.copy()
    MOCK_MODEL_STATE["bias"] = INITIAL_BIAS
    MOCK_MODEL_STATE["history"] = [
        {
            "version": "v1",
            "n_labels": 0,
            "training_agreement_pct": None,
            "created_at": "2026-11-02T10:00:00Z"
        }
    ]
    for scan_id, spots in MOCK_HOTSPOTS.items():
        for spot in spots:
            spot["properties"]["status"] = "detected"

    return {"status": "reset", "message": "Demo data restored to initial baseline."}

