import datetime
from typing import Dict, Any, List
from app.mock_data import MOCK_MODEL_STATE, MOCK_HOTSPOTS, INITIAL_WEIGHTS, INITIAL_BIAS
from app.model.calibrate import refit_logistic_model
from app.engine.scoring import score_hotspot

TRAINING_SAMPLES: List[Dict] = []
FALSE_ALARM_COUNT = 0

def record_feedback_and_recalibrate(
    hotspot_id: str,
    label_str: str,
    note: str = ""
) -> Dict[str, Any]:
    """
    Core Closed-Loop Recalibration Flow:
    1. Label Taxonomy Map:
       - Pest, Disease -> 1 (Biotic)
       - Nutrient, Water, Weeds -> 0 (Abiotic)
       - False alarm -> increments false-positive counter (excluded from logistic loss)
    2. NumPy regularized gradient descent refits weights (v1 -> v2).
    3. Re-scores all unlabelled hotspots with new model version live.
    4. Records a new ModelVersion row.
    """
    global FALSE_ALARM_COUNT

    # 1. Find the target hotspot and extract its cues
    target_hotspot = None
    target_scan_id = None
    for scan_id, spots in MOCK_HOTSPOTS.items():
        for spot in spots:
            if spot["id"] == hotspot_id:
                target_hotspot = spot
                target_scan_id = scan_id
                break
        if target_hotspot:
            break

    if not target_hotspot:
        raise ValueError(f"Hotspot '{hotspot_id}' not found.")

    # 2. Map label
    if label_str == "false_alarm":
        FALSE_ALARM_COUNT += 1
        target_hotspot["properties"]["status"] = "cleared"
        hint = "False alarm noted."
        if FALSE_ALARM_COUNT >= 3:
            hint += " Tip: Consider raising the sensitivity threshold slider to 2.2."
        return {
            "model_version": MOCK_MODEL_STATE["active_version"],
            "status": "cleared",
            "false_alarms": FALSE_ALARM_COUNT,
            "hint": hint
        }

    # Biotic vs Abiotic binary classification mapping
    binary_label = 1 if label_str in ["pest", "disease"] else 0
    cues = target_hotspot["properties"]["cues"]

    TRAINING_SAMPLES.append({
        "hotspot_id": hotspot_id,
        "cues": cues,
        "label": binary_label
    })

    # Update hotspot status
    target_hotspot["properties"]["status"] = "confirmed"

    # 3. Refit Logistic Model using NumPy Gradient Descent
    new_weights, new_bias, agreement = refit_logistic_model(
        current_weights=MOCK_MODEL_STATE["weights"],
        current_bias=MOCK_MODEL_STATE["bias"],
        prior_weights=INITIAL_WEIGHTS,
        training_data=TRAINING_SAMPLES,
        lambda_reg=0.4,
        epochs=35
    )

    # 4. Bump Model Version
    prev_version = MOCK_MODEL_STATE["active_version"]
    new_v_num = int(prev_version.replace("v", "")) + 1
    new_version_str = f"v{new_v_num}"

    MOCK_MODEL_STATE["active_version"] = new_version_str
    MOCK_MODEL_STATE["n_labels"] = len(TRAINING_SAMPLES)
    MOCK_MODEL_STATE["training_agreement_pct"] = agreement
    MOCK_MODEL_STATE["weights"] = new_weights
    MOCK_MODEL_STATE["bias"] = new_bias

    MOCK_MODEL_STATE["history"].append({
        "version": new_version_str,
        "n_labels": len(TRAINING_SAMPLES),
        "training_agreement_pct": agreement,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z"
    })

    # 5. Live Re-Score Remaining Unlabelled Hotspots
    if target_scan_id and target_scan_id in MOCK_HOTSPOTS:
        for spot in MOCK_HOTSPOTS[target_scan_id]:
            if spot["properties"]["status"] != "confirmed":
                b_score, b_class, tier, conf, contribs = score_hotspot(
                    cues=spot["properties"]["cues"],
                    weights=new_weights,
                    bias=new_bias,
                    image_quality=0.94,
                    tile_count=4
                )
                spot["properties"]["biotic_score"] = b_score
                spot["properties"]["class"] = b_class
                spot["properties"]["tier"] = tier
                spot["properties"]["confidence"] = conf
                spot["properties"]["contributions"] = contribs

    return {
        "model_version": new_version_str,
        "n_labels": len(TRAINING_SAMPLES),
        "agreement_pct": agreement,
        "weights": new_weights,
        "bias": new_bias
    }

